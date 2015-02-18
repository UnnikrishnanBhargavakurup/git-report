/**
 * For data in the webpage from python.
 * @param data
 *  JSON object contains data form python 
 */
function jscallback(data) {
  (function($) {
    $("#content").html("");
    var commits = data.commits;
    var user_info = "<div class='row'>";
    var user_percent = "<div class='row'>";
    for(i = 1; i <= commits.length; i++) {
      user_info += '<div class="col-lg-3 col-xs-6"> \
        <!-- small box -->\
        <div class="small-box bg-yellow">\
          <div class="inner">\
            <h4>\
              '+ commits[i - 1][0] +'\
            </h4>\
            <p>\
                Commits : '+ commits[i - 1][1] +'\
            </p>\
          </div>\
          <div class="icon">\
              <i class="ion ion-person-add"></i>\
          </div>\
          <a class="small-box-footer" href="#">\
              More info <i class="fa fa-arrow-circle-right"></i>\
          </a>\
        </div>\
      </div>';
      user_percent += '<div class="col-md-3 col-sm-6 col-xs-6 text-center">\
                          <input readonly type="text" class="knob" value="'+ Math.round((commits[i - 1][1] * 100) / data.total) +'" data-width="90" data-height="90" data-fgColor="#3c8dbc"/>\
                          <div class="knob-label">'+ commits[i - 1][0] +'</div>\
                      </div><!-- ./col -->';
      if(i / 4 == 0) {
        user_info += "</div><div class='row'>";
        user_percent += "</div><div class='row'>";
      }
    }
    if(i / 4 != 0) {
      user_info += "</div>";
      user_percent += "</div>";
    }
    $("#content").html(user_info);
    $("#content").append(user_percent);
    init_knob();
    var fils_cmtd = data.cm_fls;
    var usr_cm_fls = "<div id='cm-fls'>";
    for(cm_fls in fils_cmtd) {
      usr_cm_fls += "<div class='row'>";
      usr_cm_fls += "<div class='col-lg-offset-1 col-lg-8'>";
      usr_cm_fls += "<h4>"+ cm_fls +"</h4>";
      usr_cm_fls += "<table class='table table-bordered'>";
      usr_cm_fls += "<thead>\
                      <tr>\
                        <th>Files</th>\
                        <th>Commits</th>\
                      </tr>\
                    </thead>";
      for(i = 0; i < fils_cmtd[cm_fls].length; i++) {
        usr_cm_fls += "<tr>";
        usr_cm_fls +=   "<td>"+ fils_cmtd[cm_fls][i][0] +"</td>";
        usr_cm_fls +=   "<td>"+ fils_cmtd[cm_fls][i][1] +"</td>";
        usr_cm_fls += "</tr>";
      }
      usr_cm_fls += "</table>"; 
      usr_cm_fls += "</div>";
      usr_cm_fls += "</div>"
    }
    usr_cm_fls += "</div>"
    $("#content").append(usr_cm_fls);
    $(".table").dataTable( {
        "ordering": false,
        "searching" : false,
        "lengthChange" : false,
        "info":     false
    } );
  })(jQuery);
}

/**
 * For initilizing the persentage controles
 */
function init_knob() {
  (function($) {
    $(".knob").knob({
      readOnly : true,
      draw: function() {

          // "tron" case
          if (this.$.data('skin') == 'tron') {

              var a = this.angle(this.cv)  // Angle
                      , sa = this.startAngle          // Previous start angle
                      , sat = this.startAngle         // Start angle
                      , ea                            // Previous end angle
                      , eat = sat + a                 // End angle
                      , r = true;

              this.g.lineWidth = this.lineWidth;

              this.o.cursor
                      && (sat = eat - 0.3)
                      && (eat = eat + 0.3);

              if (this.o.displayPrevious) {
                  ea = this.startAngle + this.angle(this.value);
                  this.o.cursor
                          && (sa = ea - 0.3)
                          && (ea = ea + 0.3);
                  this.g.beginPath();
                  this.g.strokeStyle = this.previousColor;
                  this.g.arc(this.xy, this.xy, this.radius - this.lineWidth, sa, ea, false);
                  this.g.stroke();
              }

              this.g.beginPath();
              this.g.strokeStyle = r ? this.o.fgColor : this.fgColor;
              this.g.arc(this.xy, this.xy, this.radius - this.lineWidth, sat, eat, false);
              this.g.stroke();

              this.g.lineWidth = 2;
              this.g.beginPath();
              this.g.strokeStyle = this.o.fgColor;
              this.g.arc(this.xy, this.xy, this.radius - this.lineWidth + 1 + this.lineWidth * 2 / 3, 0, 2 * Math.PI, false);
              this.g.stroke();

              return false;
          }
      }
    });
    /* END JQUERY KNOB */
  })(jQuery);
}