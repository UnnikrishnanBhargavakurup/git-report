#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import os
from git import *
import collections
import json

#you need to import webkit and gobject, gobject is needed for threads
import webkit
import gobject

class GitReport:
    def delete_event(self, widget, event, data = None):
        return False

    def destroy(self, widget, data = None):
        gtk.main_quit()

    def __init__(self):
        gobject.threads_init()
        self.window = gtk.Window()
        self.window.set_resizable(True)
        self.window.maximize()
        #inititlize the repo url.
        self.repodir = ""
        #exit the app
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)

        #webkit.WebView allows us to embed a webkit browser
        self.web_view = webkit.WebView()
        settings = self.web_view.get_settings()
        #no need for the context context menu provided by webkit.
        settings.set_property('enable-default-context-menu', False)
        base_path = os.path.dirname(os.path.realpath(__file__));
        self.web_view.open("file:///" + base_path + "/html/index.html")
        self.window.set_icon_from_file(base_path + "/images/icon.png")
        toolbar = gtk.Toolbar()

        #create button to open git repo.
        self.add_button = gtk.ToolButton(gtk.STOCK_OPEN)
        self.add_button.connect("clicked", self.open_repo)

        #for generating report
        self.go_button = gtk.ToolButton(gtk.STOCK_OK)
        self.go_button.connect("clicked", self.get_report)


        #add the buttons to the toolbar
        toolbar.add(self.add_button)

        #entry bar for repo path.
        self.url_bar = gtk.Entry()
        self.url_bar.set_width_chars(100)
        self.url_bar.set_editable(False)
        self.url_bar.connect("activate", self.open_repo)

        item = gtk.ToolItem()
        item.add(self.url_bar)
        toolbar.add(item)

        toolbar.add(self.go_button)

        #anytime a site is loaded the update_buttons will be called
        self.web_view.connect("load_committed", self.update_buttons)

        scroll_window = gtk.ScrolledWindow(None, None)
        scroll_window.add(self.web_view)
        
        # Create a menu-bar to hold the menus and add it to our main window
        menu_bar = gtk.MenuBar()
        vbox = gtk.VBox(False, 0)

        # For menus 
        f_smenu = gtk.Menu()

        # For open menu item
        menu_items = gtk.MenuItem("Open")
        #and add it to the menu.
        f_smenu.append(menu_items)
        # Open the dialog for selecting repo.
        menu_items.connect("activate", self.open_repo)
        # Show the widget
        menu_items.show()

        # For exit menu item
        menu_items = gtk.MenuItem("Exit")
        #and add it to the menu.
        f_smenu.append(menu_items)
        # Open the dialog for selecting repo.
        menu_items.connect("activate", self.destroy)
        # Show the widget
        menu_items.show()

        file_menu = gtk.MenuItem("File")
        file_menu.show()
        # Now we specify that we want our newly created "menu" to be the
        # menu for the "file menu"
        file_menu.set_submenu(f_smenu)

        # For menus 
        about_smenu = gtk.Menu()

        # For open menu item
        menu_items = gtk.MenuItem("About")
        #and add it to the menu.
        about_smenu.append(menu_items)
        # Open the dialog for selecting repo.
        menu_items.connect("activate", self.show_about, "")
        # Show the widget
        menu_items.show()

        about_menu = gtk.MenuItem("Help")
        about_menu.show()
        # Now we specify that we want our newly created "menu" to be the
        # menu for the "file menu"
        about_menu.set_submenu(about_smenu)

        vbox.pack_start(menu_bar, False, False, 2)
        menu_bar.show()
        menu_bar.append(file_menu)
        menu_bar.append(about_menu)

        vbox.pack_start(toolbar, False, True, 0)
        vbox.add(scroll_window)

        self.window.add(vbox)
        self.window.show_all()

    def open_repo(self, widget, data=None):
        '''Open the file browser dialog to select the repository for generating 
        the report.'''
        dialog = gtk.FileChooserDialog("Open a git repository (a path containing .git folder)",
                                       None,
                                       gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        #default home folder.
        dialog.set_current_folder(os.environ['HOME'])
        dialog.set_show_hidden(True)
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*.git")
        dialog.add_filter(filter)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            if os.path.isdir(os.path.join(dialog.get_filename(), '.git')):
                self.repodir = dialog.get_filename()
                self.url_bar.set_text(dialog.get_filename())
                self.go_button.set_sensitive(True)
            else:
                md = gtk.MessageDialog(self.window, 
                    gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, 
                    gtk.BUTTONS_CLOSE, "Please select a valid git repository")
                md.run()
                md.destroy()
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()
    def get_report(self, widget, data=None):
        '''Generate report from the repository.'''
        if self.repodir == "":
            md = gtk.MessageDialog(self.window, 
                gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, 
                gtk.BUTTONS_CLOSE, "Please select a valid git repository")
            md.run()
            md.destroy()  
            return          
        try:
            repo = Repository(self.repodir)
            log = repo.run_cmd(['log', '--pretty=format:%an'])
            cm_list = log.splitlines();
            total_commits = [[x, cm_list.count(x)] for x in set(cm_list)]
            _total = 0;
            user_commits = {}
            for x in total_commits:
              _total += x[1];
              user_commits[x[0]] = self.commits_by_user(x[0], repo);
            data = {
              "commits" : total_commits, 
              "total" : _total,
              "cm_fls" : user_commits
            }
            self.web_view.execute_script("jscallback(%s)" % json.dumps(data))
        except GitError, msg:
            print str(msg)
    def commits_by_user(self, user, repo):
        '''For getting the total commits by a user in each files in the repository'''
        log = repo.run_cmd(['log', '--name-status', '--pretty=%H', '--author=' + user])
        cm_list = log.splitlines();
        cm_files = []
        for line in cm_list:
          # for getting the modified file by the user.
          if line.startswith("M"):
            cm_files.append(line[2:])
        total_commits = [[x, cm_files.count(x)] for x in set(cm_files)]
        return total_commits;
    def update_buttons(self, widget, data=None):
        '''Make the apply button disabled initially.'''
        self.url_bar.set_text("")
        self.add_button.set_sensitive(True)
        self.go_button.set_sensitive(True)
    def show_about(self, widget, data):
        # The AboutDialog has good helper methods which
        # setup the dialog and add the content ensuring all
        # about dialog are consistant.  Below is a small example
        # Create AboutDialog object
        dialog = gtk.AboutDialog()
        # Add the application name to the dialog
        dialog.set_name('GitReport')
        # Set the application version
        dialog.set_version('0.1.1')
        # Pass a list of authors.  This is then connected to the 'Credits'
        # button.  When clicked the buttons opens a new window showing
        # each author on their own line.
        dialog.set_authors(['Unnikrishnan Bhargavakurup (unnikrishnanadoor@gmail.com)', 'Anto Jose (antojose.th@gmail.com)'])
        # Add a short comment about the application, this appears below the application
        # name in the dialog
        dialog.set_comments('GUI for showing commit summary of a git repository.')
        # Add license information, this is connected to the 'License' button
        # and is displayed in a new window.
        dialog.set_license('Distributed under the GPLv2 license.\nhttp://www.gnu.org/licenses/gpl-2.0.html')
        # Show the dialog
        dialog.run()
        # The destroy method must be called otherwise the 'Close' button will
        # not work.
        dialog.destroy()
    def main(self):
        gtk.main()

if __name__ == "__main__":
    git_report = GitReport()
    git_report.main()
