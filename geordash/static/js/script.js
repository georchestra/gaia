const baseurl = '/' + window.location.pathname.split('/')[1]

const fetchForHome = () => {
  fetch(baseurl + '/api/geonetwork/metadatas.json')
    .then(response => response.json())
    .then(mydata => {
        var $table = $('#table');
        var xxdata = [];
        if(mydata.length == 0) {
            $table.remove();
            $('#mdtitle').remove();
            return;
        }
        $('#mdtitle').text(mydata.length + ' metadatas');
        mydata.forEach(function (value) {
            value['dhlink']='<a href="/datahub/dataset/' + value['_id'] + '">voir</a>';
            value['editlink']='<a href="/geocat/srv/fre/catalog.edit#/metadata/' + value['gnid'] +'?redirectUrl=catalog.edit">editer</a>';
            xxdata.push(value);
        });
        $(function() {
            $table.bootstrapTable({data: xxdata});
        });
    })
    .catch(function(err) {
      $('#md').remove()
    });

  fetch(baseurl + '/api/mapstore/maps.json')
    .then(response => response.json())
    .then(mydata => {
        var $table = $('#mapstable');
        var xxdata = [];
        res = mydata['results'];
        if(mydata['totalCount'] == 0) {
            $table.remove();
            $('#mapstitle').remove();
            return;
        }
        $('#mapstitle').text(mydata['totalCount'] + ' maps');
        res.forEach(function (value) {
            id = value['id'];
            value['id'] = '<a href="' + baseurl + '/map/' + id + '">' + id + '</a>';
            value['viewlink']='<a href="/mapstore/#/viewer/' + id + '">voir</a>';
            xxdata.push(value);
        });
        $(function() {
            $table.bootstrapTable({data: xxdata});
        });
    })
    .catch(function(err) {
      $('#mapstable').remove();
      $('#mapstitle').remove();
    });

  fetch(baseurl + '/api/mapstore/contexts.json')
    .then(response => response.json())
    .then(mydata => {
        var $table = $('#ctxtable');
        var xxdata = [];
        res = mydata['results'];
        if(mydata['totalCount'] == 0) {
            $table.remove();
            $('#ctxtitle').remove();
            return;
        }
        $('#ctxtitle').text(mydata['totalCount'] + ' contexts');
        res.forEach(function (value) {
            id = value['id'];
            value['id'] = '<a href="' + baseurl + '/context/' + id + '">' + id + '</a>';
            value['viewlink']='<a href="/mapstore/#/context/' + value['name'] + '">voir</a>';
            value['editlink']='<a href="/mapstore/#/context-creator/' + id + '">editer</a>';
            xxdata.push(value);
        });
        $(function() {
            $table.bootstrapTable({data: xxdata});
        });
    })
    .catch(function(err) {
      $('#ctxtable').remove();
      $('#ctxtitle').remove();
    });

}

const DisplayPrev = (type, resid, taskids, showdelete, targetdivid = '#previouslist') => {
    if (taskids === null) { return ; }
    const sorted = taskids.sort((a,b)=>new Date(b['finished']) - new Date(a['finished']));
    const targettitledivid = targetdivid.replace('#previouslist', '#pbtitle')
    const arr = sorted.map(t => {
        const link = $("<a>");
        link.attr("id", 'display-taskres-' + t['id'])
        link.attr("href","javascript:PollTaskRes('" + type +"','"+ resid + "','" + t['id'] + "'," + showdelete + ",'" + targettitledivid + "');");
        link.attr("title","Show result for task " + t['id']);
        link.text("check at " + t['finished']);
        if (showdelete) {
          const link2 = $("<a>");
          link2.attr("href","javascript:DeleteTask('" + t['id'] + "');");
          link2.attr("title","Forget result for task " + t['id']);
          link2.html('<i class="bi bi-trash"></i>');
          return [ link[0], "&nbsp;", link2[0] ];
        }
        return link[0];
    });
    $(targetdivid).html(ArrayToHtmlList(arr));
}

const ReloadCapabilities = (type, url) => {
  fetch(baseurl + '/tasks/forgetogc/'+ type + '/' + url)
    .then(response => response.json())
    .then(res => {
        if (res['deleted'] > 0) {
          $('#reloadlink').text("Reloading..");
          location.reload()
        }
    })
}

const GetPbStr = (p) => {
  if (p instanceof String) {
    return p
  }
  switch(p.type) {
    /* from ows */
    case 'NoMetadataUrl':
      return `Layer has no metadataurl`
    case 'BrokenMetadataUrl':
      return `Layer has a broken metadataurl: ${p.url} returns ${p.code}`
    case 'MissingMdUuid':
      return `Layer points at a metadauuid ${p.uuid} that was not found in local csw`
    case 'NoSuchOwsOperation':
      return `service doesnt support ${p.operation} operation`
    case 'UnexpectedReturnedFormat':
      return `${p.operation} succeded but returned format ${p.returned} didn't match expected ${p.expected}`
    case 'UnexpectedContentLength':
      return `${p.operation} succeded but the result size was ${p.length}`
    case 'UnexpectedFirstXmlTag':
      return `${p.operation} succeeded but the first XML tag was ${p.first_tag} instead of ${p.expected}`
    case 'ExpectedXML':
      return `${p.operation} succeeded but didnt return XML ? ${p.return}`
    case 'ServiceException':
      return `Failed ${p.operation} on layer '${p.layername}' in ${p.stype} at ${p.url}, got ${p.e}: ${p.estr}`
    case 'ForbiddenAccess':
      return `Got a 403 for ${p.operation} on layer '${p.layername}' in ${p.stype} at ${p.url}`
    /* from mapstore */
    case 'NoSuchLayer':
      return `Layer '${p.lname}' doesnt exist in ${p.stype} service at ${p.url}`
    case 'OGCException':
      return `No ${p.stype} service at ${p.url}, got ${p.exception}: ${p.exceptionstr}`
    case 'BrokenDatasetUrl':
      return `Non-working dataset url: ${p.url} returns ${p.code}`
    case 'ConnectionFailure':
      return `Connection failure for url at ${p.url}, got ${p.exception}: ${p.exceptionstr}`
    /* from csw */
    case 'BrokenProtocolUrl':
      return `Non-working ${p.protocol} url: ${p.url} returns ${p.code}`
    case 'EmptyUrl':
      return `Missing URL for ${p.protocol} entry`
    case 'NoSuchMetadata':
      return `Metadata with uuid ${p.uuid} doesnt exist in CSW service at ${p.url}`
    case 'MdHasNoLinks':
      return `No links to OGC layers or download links ?`
    default:
      return `Unhandled error code ${p.type} for problem ${p}`
  }
}
const ArrayToHtmlList = (array) => {
  const list = $('<ol>').append(
    array.map(p => $("<li>").html(p))
  );
  return list;
}

const DeleteTask = (taskid) => {
  fetch(baseurl + '/tasks/forget/' + taskid)
    .then(response => {
      if (response.status != 403) {
        $('#display-taskres-' + taskid).parent().remove();
      }
    });
}

const CheckRes = (type, resid, showdelete, targetdivid = '#pbtitle') => {
  fetch(baseurl + '/tasks/check/' + type + '/' + resid + '.json')
    .then(response => response.json())
    .then(mydata => {
        $(targetdivid).text("En cours d'analyse");
        PollTaskRes(type, resid, mydata["result_id"], showdelete, targetdivid);
    });
}

const PollTaskRes = (type, resid, taskid, showdelete, targetdivid = '#pbtitle') => {
    const poll = () => {
        const targetpbdivid = targetdivid.replace('#pbtitle', '#problems')
        const targetpreviousdivid = targetdivid.replace('#pbtitle', '#previouslist')
        const targetpbdetdivid = targetdivid.replace('#pbtitle', '#pbdetails')
        fetch(baseurl + '/tasks/result/' + taskid)
            .then(response => response.json())
            .then(data => {
//                console.log(data)
                if (data === null) {
                  $(targetdivid).text('got null, shouldnt happen ?');
                } else if(!data["ready"]) {
                  if (data['completed'] !== null) {
                    $(targetdivid).text(data["completed"]);
                  } else {
                    $(targetdivid).text('Waiting');
                  }
                  setTimeout(poll, 500)
                } else if (!data["successful"]) {
                  $(targetdivid).text("Protch !");
                  $(targetpbdivid).text('Something crashed, check browser console');
                  console.error(data)
                } else {
                  if (Array.isArray(data["value"])) {
                      var p = data['value'].filter(function(f) {
                        return f['problems'].length > 0
                      });
                      const probs = p.map(j => {
                        return j.problems.map(i => {
                          if (Array.isArray(j.args)) {
                            if (data['task'].includes('check_resources')) {
                              // mapstore resources
                              if (j.args[0] == 'MAP') {
                                xurl = baseurl + '/map/' + j.args[1]
                              } else {
                                xurl = baseurl + '/context/' + j.args[1]
                              }
                              return {'url': `${j.args[0]} ${j.args[1]}`, 'xurl': xurl, 'problem': GetPbStr(i) }
                            } else {
                              // csw
                              if (data['task'].includes('csw') && j.args.length == 2) {
                                xurl = baseurl + '/csw/' + j.args[0].split('/')[2] + '/' + j.args[1]
                              } else {
                              // ogc
                                xurl = baseurl + '/ows/' + j.args[0] + '/' + j.args[1].replaceAll('/','~') + '/' + j.args[2]
                              }
                              return {'url': j.args[j.args.length-1], 'xurl': xurl, 'problem': GetPbStr(i) }
                            }
                          } else {
                            // mapstore configs
                            return {'url': j.args, 'problem': GetPbStr(i) }
                          }
                        })
                      });
                      data["value"].problems = probs.flat(1)
                  } else {
                      const probs = data["value"].problems.map(i => {
                        return GetPbStr(i)
                      })
                      data["value"].problems = probs
                  }
                  if (data["value"].problems.length > 0) {
                    $(targetdivid).text(data["value"].problems.length + ' problems found');
                    if (Array.isArray(data["value"])) {
                        var argtitle = 'Layer'
                        if (data['task'].includes('csw')) {
                          argtitle = 'Metadata'
                        } else if (data['task'].includes('check_resources')) {
                          argtitle = 'Map/Ctxid'
                        } else if (data['task'].includes('check_configs')) {
                          argtitle = 'Configfile'
                        }
                        const pbta = $("<table>")
                        pbta.attr("data-show-columns", true)
                        pbta.attr("id", targetpbdivid + '-table')
                        const exportlink = $("<a>");
                        exportlink.attr("href",baseurl + '/tasks/result/' + taskid)
                        exportlink.attr("title","Export as JSON")
                        exportlink.html('<p class="bi bi-filetype-json">View/Export problem list as JSON</p>');
                        $(targetpbdivid).append(exportlink, pbta)
                        pbta.bootstrapTable({
                            data: data["value"].problems,
                            search: true,
                            columns: [
                              {'title': 'Index', 'formatter': 'runningFormatter'},
                              {'field': 'url', 'title': argtitle, 'formatter': 'urlFormatter'},
                              {'field': 'problem', 'title': 'Problem'}
                            ]
                          });
                    } else {
                        $(targetpbdivid).html(ArrayToHtmlList(data["value"].problems));
                    }
                  } else {
                    $(targetdivid).html('<a href="https://lessalesmajestes.bandcamp.com/album/no-problemo">No problemo!</a>')
                    $(targetpbdivid).empty();
                  }
                  const d = new Date(data["finished"] * 1000);
                  $(targetpbdetdivid).text('vérification faite le '+ d);
                  if ($(targetpreviousdivid).children().length == 0) {
                    $(targetpreviousdivid).html(ArrayToHtmlList([]));
                  }
                  if ($(targetpreviousdivid).find("#display-taskres-"+taskid).length == 0) {
                    const link = $("<a>");
                    link.attr("id", 'display-taskres-' + taskid)
                    link.attr("href","javascript:PollTaskRes('" + type +"','"+ resid + "','" + data['taskid'] + "'," + showdelete + ",'" + targetdivid + "');");
                    link.attr("title","Show result for task " + data["taskid"]);
                    link.text("check at " + d);
                    if (showdelete) {
                      const link2 = $("<a>");
                      link2.attr("href","javascript:DeleteTask('" + data["taskid"] + "');");
                      link2.attr("title","Forget result for task " + data['taskid']);
                      link2.html('<i class="bi bi-trash"></i>');
                      $(targetpreviousdivid).children(":first").prepend($("<li>").html([link[0], '&nbsp;', link2[0]]))
                    }
                    else {
                      $(targetpreviousdivid).children(":first").prepend($("<li>").html(link[0]))
                    }
                  }
                }
            })
    }
    poll();
}

function urlFormatter(value, row) {
  if (row.xurl !== undefined) {
    return '<a class="fa" href="' + row.xurl + '">'+ row.url +'</a>'
  } else {
    return row.url
  }
}
function runningFormatter(value, row, index) {
    return 1 + index;
}

const SendToMapstore = (type, url, layername) => {
    const msurl="/mapstore/#/?actions=[{\"type\":\"CATALOG:ADD_LAYERS_FROM_CATALOGS\",\"layers\":[\"" + layername + "\"],\"sources\":[{\"type\":\"" + type + "\",\"url\":\"" + url + "\"}]}]";
    window.open(msurl, "_blank");
}
