import os
import os.path
import sys
import subprocess
import re
import tempfile
import threading
from util import *


_git = None

class GitError(RuntimeError): pass

def git_binary():
    global _git

    if _git:
        return _git

    # Search for git binary
    if os.name == 'posix':
        locations = ['{PATH}/git', '/opt/local/bin/git', '/usr/local/git/bin']
    elif sys.platform == 'win32':
        locations = (r'{PATH}\git.exe', r'C:\Program Files\Git\bin\git.exe')
    else:
        locations = []

    for _git in find_binary(locations):
        return _git

    _git = None
    raise GitError, "git executable not found"

def run_cmd(dir, args, with_retcode=False, with_stderr=False, raise_error=False, input=None, env={}, run_bg=False, setup_askpass=False):
    # Check args
    if type(args) in [str, unicode]:
        args = [args]
    args = [str(a) for a in args]

    # Check directory
    if not os.path.isdir(dir):
        raise GitError, 'Directory not exists: ' + dir

    try:
        os.chdir(dir)
    except OSError, msg:
        raise GitError, msg

    # Run command
    if type(args) != list:
        args = [args]

    # Setup environment
    git_env = dict(os.environ)
    if setup_askpass and 'SSH_ASKPASS' not in git_env:
        git_env['SSH_ASKPASS'] = '%s-askpass' % os.path.realpath(os.path.abspath(sys.argv[0]))

    git_env.update(env)
    
    preexec_fn = os.setsid if setup_askpass else None
    p = Popen([git_binary()] + args, stdout=subprocess.PIPE,
              stderr=subprocess.PIPE, stdin=subprocess.PIPE,
              env=git_env, shell=False, preexec_fn=preexec_fn)
    if run_bg:
        return p

    if input == None:
        stdout,stderr = p.communicate('')
    else:
        stdout,stderr = p.communicate(utf8_str(input))
    
    # Return command output in a form given by arguments
    ret = []

    if p.returncode != 0 and raise_error:
        raise GitError, 'git returned with the following error:\n%s' % stderr

    if with_retcode:
        ret.append(p.returncode)
    ret.append(stdout)

    if with_stderr:
        ret.append(stderr)
    if len(ret) == 1:
        return ret[0]
    else:
        return tuple(ret)

class Repository(object):
    def __init__(self, repodir, name='Main module', parent=None):
        self.name = name
        self.parent = parent

        # Search for .git directory in repodir ancestors
        repodir = os.path.abspath(repodir)
        try:
            if parent:
                if not os.path.isdir(os.path.join(repodir, '.git')):
                    raise GitError, "Not a git repository: %s" % repodir
            else:
                while not os.path.isdir(os.path.join(repodir, '.git')):
                    new_repodir = os.path.abspath(os.path.join(repodir, '..'))
                    if new_repodir == repodir or (parent and new_repodir == parent.dir):
                        raise GitError, "Directory is not a git repository"
                    else:
                        repodir = new_repodir
        except OSError:
            raise GitError, "Directory is not a git repository or it is not readable"
            
        self.dir = repodir

        # Remotes
        self.config = ConfigFile(os.path.join(self.dir, '.git', 'config'))
        self.url = self.config.get_option('remote', 'origin', 'url')

        self.remotes = {}
        for remote, opts in self.config.sections_for_type('remote'):
            if 'url' in opts:
                self.remotes[remote] = opts['url']

        # Run a git status to see whether this is really a git repository
        retcode,output = self.run_cmd(['status'], with_retcode=True)
        if retcode not in [0,1]:
            raise GitError, "Directory is not a git repository"

        # Load refs
        self.load_refs()

        # Get submodule info
        self.submodules = self.get_submodules()
        self.all_modules = [self] + self.submodules

    def load_refs(self):
        self.refs = {}
        self.branches = {}
        self.remote_branches = {}
        self.tags = {}

        # HEAD, current branch
        self.head = self.run_cmd(['rev-parse', 'HEAD']).strip()
        self.current_branch = None
        try:
            f = open(os.path.join(self.dir, '.git', 'HEAD'))
            head = f.read().strip()
            f.close()

            if head.startswith('ref: refs/heads/'):
                self.current_branch = head[16:]
        except OSError:
            pass

        # Main module references
        if self.parent:
            self.main_ref = self.parent.get_submodule_version(self.name, 'HEAD')
            if os.path.exists(os.path.join(self.parent.dir, '.git', 'MERGE_HEAD')):
                self.main_merge_ref = self.parent.get_submodule_version(self.name, 'MERGE_HEAD')
            else:
                self.main_merge_ref = None
        else:
            self.main_ref = None
            self.main_merge_ref = None

        # References
        for line in self.run_cmd(['show-ref']).split('\n'):
            commit_id, _, refname = line.partition(' ')
            self.refs[refname] = commit_id

            if refname.startswith('refs/heads/'):
                branchname = refname[11:]
                self.branches[branchname] = commit_id
            elif refname.startswith('refs/remotes/'):
                branchname = refname[13:]
                self.remote_branches[branchname] = commit_id
            elif refname.startswith('refs/tags/'):
                # Load the referenced commit for tags
                tagname = refname[10:]
                try:
                    self.tags[tagname] = self.run_cmd(['rev-parse', '%s^{commit}' % refname], raise_error=True).strip()
                except GitError:
                    pass

        # Inverse reference hashes
        self.refs_by_sha1 = invert_hash(self.refs)
        self.branches_by_sha1 = invert_hash(self.branches)
        self.remote_branches_by_sha1 = invert_hash(self.remote_branches)
        self.tags_by_sha1 = invert_hash(self.tags)

    def run_cmd(self, args, **opts):
        return run_cmd(self.dir, args, **opts)

    def get_submodules(self):
        # Check existence of .gitmodules
        gitmodules_path = os.path.join(self.dir, '.gitmodules')
        if not os.path.isfile(gitmodules_path):
            return []

        # Parse .gitmodules file
        repos = []
        submodule_config = ConfigFile(gitmodules_path)
        for name,opts in submodule_config.sections_for_type('submodule'):
            if 'path' in opts:
                repo_path = os.path.join(self.dir, opts['path'])
                repos.append(Repository(repo_path, name=opts['path'], parent=self))

        return repos

    def get_submodule_version(self, submodule_name, main_version):
        dir = os.path.dirname(submodule_name)
        name = os.path.basename(submodule_name)
        output = self.run_cmd(['ls-tree', '-z', '%s:%s' % (main_version, dir)])
        for line in output.split('\x00'):
            if not line.strip(): continue

            meta, filename = line.split('\t')
            if filename == name:
                mode, filetype, sha1 = meta.split(' ')
                if filetype == 'commit':
                    return sha1

        return None


class ConfigFile(object):
    def __init__(self, filename):
        self.sections = []

        # Patterns
        p_rootsect = re.compile(r'\[([^\]\s]+)\]')
        p_sect     = re.compile(r'\[([^\]"\s]+)\s+"([^"]+)"\]')
        p_option   = re.compile(r'(\w+)\s*=\s*(.*)')

        # Parse file
        section = None
        section_type = None
        options = {}

        f = open(filename)
        for line in f:
            line = line.strip()

            if len(line) == 0 or line.startswith('#'):
                continue

            # Parse sections
            m_rootsect = p_rootsect.match(line)
            m_sect     = p_sect.match(line)

            if (m_rootsect or m_sect) and section:
                self.sections.append( (section_type, section, options) )
            if m_rootsect:
                section_type = None
                section = m_rootsect.group(1)
                options = {}
            elif m_sect:
                section_type = m_sect.group(1)
                section = m_sect.group(2)
                options = {}
                
            # Parse options
            m_option = p_option.match(line)
            if section and m_option:
                options[m_option.group(1)] = m_option.group(2)

        if section:
            self.sections.append( (section_type, section, options) )
        f.close()

    def has_section(self, sect_type, sect_name):
        m = [ s for s in self.sections if s[0]==sect_type and s[1] == sect_name ]
        return len(m) > 0

    def sections_for_type(self, sect_type):
        return [ (s[1],s[2]) for s in self.sections if s[0]==sect_type ]

    def options_for_section(self, sect_type, sect_name):
        m = [ s[2] for s in self.sections if s[0]==sect_type and s[1] == sect_name ]
        if m:
            return m[0]
        else:
            return None

    def get_option(self, sect_type, sect_name, option):
        opts = self.options_for_section(sect_type, sect_name)
        if opts:
            return opts.get(option)
        else:
            return None

