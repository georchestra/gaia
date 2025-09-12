const baseurl = '/' + window.location.pathname.split('/')[1]

const fetchForHome = (widgets) => {
  widgets.forEach(function(o) {
    fetch(baseurl + '/tasks/lastresultbytask/' + o["taskname"] + "?taskargs=" + o["taskargs"].join(","))
      .then(response => response.json())
      .then(mydata => {
        if (parseInt(mydata["finished"])) {
          const d = new Date(mydata["finished"] * 1000);
          $(o["prefix"] + '-lastupdated').html("Information valid as of "+ d.toLocaleString("fr-FR") + '<br/>(taskid: '+ mydata['taskid'] + ')')
        }
        if (mydata === "notask") {
          $(o["prefix"] + '-abstract').html("<span class='text-warning'>no " + o["taskname"] + " job found with args " + o["taskargs"].join(",") + ", something went wrong ?</span>")
          return;
        }
        if (mydata['value'] === null && mydata['ready'] === false) {
          $(o["prefix"] + '-abstract').html("<span class='text-primary'>job is currently running, " + mydata['completed'] + " objects checked</span>")
          return;
        }
        let str = "<span class='text-success'>" + mydata['value'].length + ' entries</span><br/>';
        let errors = 0;
        let objWithErrors = 0;
        mydata['value'].forEach(obj => {
          const nerrors = obj['problems'].length;
          if (nerrors > 0) {
            errors += nerrors;
            objWithErrors += 1;
          }
        });
        if (errors > 0) {
          str += "<span class='text-danger'>" + errors + " errors found in " + objWithErrors + " objects !</span>";
        } else {
          str += "<span class='text-success'> no errors !</span>";
        }
        $(o["prefix"] + '-abstract').html(str);
    })
    .catch(function(err) {
      $(o["prefix"] + '-abstract').html("<span class='bg-danger text-white'>something went wrong</span>")
    });
  })
}

const fetchForHomeSingleTask = (widgets) => {
  widgets.forEach(function(o) {
    fetch(baseurl + '/tasks/lastresultbytask/' + o["taskname"] + "?taskargs=" + o["taskargs"].join(","))
      .then(response => response.json())
      .then(mydata => {
        if (parseInt(mydata["finished"])) {
          const d = new Date(mydata["finished"] * 1000);
          $(o["prefix"] + '-lastupdated').html("Information valid as of "+ d.toLocaleString("fr-FR") + '<br/>(taskid: '+ mydata['taskid'] + ')')
        }
        if (mydata === "notask") {
          $(o["prefix"] + '-abstract').html("<span class='text-warning'>no " + o["taskname"] + " job found with args " + o["taskargs"].join(",") + ", something went wrong ?</span>")
          return;
        }
        if (mydata['value'] === null && mydata['ready'] === false) {
          $(o["prefix"] + '-abstract').html("<span class='text-primary'>job is currently running, " + mydata['completed'] + " objects checked</span>")
          return;
        }
        let str = "<span class='text-success'>" + mydata['value']['problems'].length + ' entries</span><br/>';

        const nerrors = mydata['value']['problems'].length;

        if (nerrors > 0) {
          str += "<span class='text-danger'>" + nerrors + " errors found !</span>";
        } else {
          str += "<span class='text-success'> no errors !</span>";
        }
        $(o["prefix"] + '-abstract').html(str);
    })
    .catch(function(err) {
      $(o["prefix"] + '-abstract').html("<span class='bg-danger text-white'>something went wrong</span>")
    });
  })
}

const fetchMyMd = (localgnbaseurl) => {
  fetch(baseurl + '/api/geonetwork/metadatas.json')
    .then(response => response.json())
    .then(mydata => {
        var $table = $('#table');
        var xxdata = [];
        if(mydata.length == 0) {
            $('#md').html("<span class='text-warning'>vous n'avez aucune métadonnée ?</span>")
            return;
        }
        $('#mdtitle').text(mydata.length + ' metadatas');
        mydata.forEach(function (value) {
            if (value['gaialink']) {
              value['uuid'] = '<a href="' + baseurl + '/csw/srv/' +value['_id'] + '">' + value['_id'] + '</a>';
            } else {
              value['uuid'] = value['_id'];
            }
            value['dhlink']='<a href="/datahub/dataset/' + value['_id'] + '">voir</a>';
            value['editlink']='<a href="/' + localgnbaseurl + '/srv/fre/catalog.edit#/metadata/' + value['gnid'] +'?redirectUrl=catalog.edit">editer</a>';
            xxdata.push(value);
        });
        $(function() {
            $table.bootstrapTable({data: xxdata});
        });
    })
    .catch(function(err) {
      $('#md').html("<span class='bg-danger text-white'>something went wrong fetching your metadatas</span>")
    });
}

const fetchMyMaps = () => {
  fetch(baseurl + '/api/mapstore/maps.json')
    .then(response => response.json())
    .then(mydata => {
        var $table = $('#mapstable');
        var xxdata = [];
        res = mydata['results'];
        if(mydata['results'].length == 0) {
            $('#maps').html("<span class='text-warning'>Aucune carte ?</span>")
            return;
        }
        $('#mapstitle').text(mydata['results'].length + ' maps');
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
      $('#maps').html("<span class='bg-danger text-white'>something went wrong fetching maps</span>")
    });

  fetch(baseurl + '/api/mapstore/contexts.json')
    .then(response => response.json())
    .then(mydata => {
        var $table = $('#ctxtable');
        var xxdata = [];
        res = mydata['results'];
        if(mydata['results'].length == 0) {
            $('#ctx').html("<span class='text-warning'>Aucune application ?</span>")
            return;
        }
        $('#ctxtitle').text(mydata['results'].length + ' applications');
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
      $('#ctx').html("<span class='bg-danger text-white'>something went wrong fetching contexts</span>")
    });

}

const fetchMapsAndCtxCount = (mymaplink) => {
  fetch(baseurl + '/api/mapstore/maps.json')
    .then(response => response.json())
    .then(mydata => {
        res = mydata['results'];
        if(res.length == 0) {
            $('#ms-map-abstract').html("<span class='text-warning'>Aucune carte ?</span>")
        } else {
            $('#ms-map-abstract').html("<span class='text-success'>Vous avez accès à <a href='" + mymaplink + "'>" + res.length + " cartes</a></span>")
        }
        $('#ms-map-lastupdated').remove()
    })
    .catch(function(err) {
      $('#ms-map-abstract').html("<span class='bg-danger text-white'>something went wrong fetching maps</span>")
    });
  fetch(baseurl + '/api/mapstore/contexts.json')
    .then(response => response.json())
    .then(mydata => {
        res = mydata['results'];
        if(mydata['results'].length == 0) {
            $('#ms-ctx-abstract').html("<span class='text-warning'>Aucune application ?</span>")
        } else {
            $('#ms-ctx-abstract').html("<span class='text-success'>Vous avez accès à <a href='" + mymaplink + "'>" + res.length + " applications</a></span>")
        }
        $('#ms-ctx-lastupdated').remove()
    })
    .catch(function(err) {
      $('#ms-ctx-abstract').html("<span class='bg-danger text-white'>something went wrong fetching contexts</span>")
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
        const d = new Date(t["finished"] * 1000);
        link.text("check at " + d.toLocaleString("fr-FR"));
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
    case 'XMLParseError':
      return `${p.operation} succeeded but failed parsing XML ? ${p.return}`
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
    case 'NoSuchSld':
      return `Sld with url ${p.url} doesnt exist`
    case 'NoSuchResource':
      return `Resource '${p.restype}' with id '${p.resid}' doesnt exist`
    /* from gsd */
    case 'EmptyWorkspace':
      return `Workspace '${p.skey}' is empty`
    case 'EmptyConnUrl':
      return `DataStore '${p.skey}' has no connurl`
    case 'NoSuchFile':
      return `'${p.skey}' refers to file ${p.path} which doesnt exist`
    case 'NoSuchDir':
      return `'${p.skey}' refers to directory ${p.path} which doesnt exist`
    case 'NoSuchVectorData':
      return `'${p.skey}' refers to vector data ${p.vdk.replaceAll('~','/')} which wasnt found in gs datadir`
    case 'NoSuchRasterData':
      return `'${p.skey}' refers to raster data ${p.rdk.replaceAll('~','/')} which wasnt found in gs datadir`
    case 'NoSuchSchema':
      return `'${p.skey}' refers to database schema ${p.schema} which wasnt found in ${p.database}`
    case 'NoSuchWorkspace':
      return `${p.stype} '${p.skey}' refers to workspace ${p.wsid} which doesnt exist`
    case 'NoSuchNamespace':
      return `${p.stype} '${p.skey}' refers to namespace ${p.nsid} which doesnt exist`
    case 'NoSuchDatastore':
      return `FeatureType '${p.skey}' refers to datastore ${p.dsid} which doesnt exist`
    case 'NoSuchTableInSchema':
      return `FeatureType '${p.skey}' refers to table/view ${p.table} in schema ${p.schema} which doesnt exist`
    case 'NoSuchFeatureType':
      return `Layer '${p.skey}' refers to featuretype ${p.ftid} which doesnt exist`
    case 'NoSuchCoverage':
      return `Layer '${p.skey}' refers to coverage ${p.cid} which doesnt exist`
    case 'NoSuchCoveragestore':
      return `Coverage '${p.skey}' refers to coveragestore ${p.dsid} which doesnt exist`
    case 'NoSuchStyle':
      return `Layer '${p.skey}' refers to style ${p.sid} which doesnt exist`
    case 'LayerHasNoDefaultStyle':
      return `Layer '${p.skey}' has no default style`
    case 'NotTileindex':
      return `VectorData '${p.vdk}' doesnt look like a TileIndex`
    case 'StyleInGlobalWorkspace':
      return `Style '${p.skey}' isnt in a workspace`
    case 'NoSuchSLD':
      return `Style '${p.skey}' refers to an SLD in ${p.path.replaceAll('~','/')} which doesnt exist`
    case 'EmptySLD':
      return `SLD '${p.skey.replaceAll('~','/')}' is empty`
    case 'DefaultSLD':
      return `SLD '${p.skey.replaceAll('~','/')}' is likely a default generic style`
    case 'UnusedSLD':
      return `SLD '${p.skey.replaceAll('~','/')}' is unused (eg not referenced by any style)`
    case 'UnusedStyle':
      return `Style '${p.skey}' is unused (eg not referenced by any layer)`
    case 'UnusedRasterData':
      return `RasterData '${p.skey.replaceAll('~','/')}' is unused`
    case 'UnusedVectorData':
      return `VectorData '${p.skey.replaceAll('~','/')}' is unused`
    case 'UnusedFileRes':
      return `Folder is useless '${p.path}' with size ' ${ p.size } '`
    case 'UnusedFileResTotal':
      return `In total '${p.size}' could be saved on '${p.total}'`
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

const ParseGSDD = () => {
  const targetdivid = '#progress';
  fetch(baseurl + '/tasks/parsegsd.json')
    .then(response => response.json())
    .then(mydata => {
      $(targetdivid).text("Queuing background task..");
      const poll = () => {
        fetch(baseurl + '/tasks/taskresults/' + mydata["taskid"])
          .then(response => response.json())
          .then(data => {
            console.log(data)
            if (data === null) {
              $(targetdivid).text('got null, shouldnt happen ?');
            } else if (!data["state"] || data["state"] == 'FAILURE') {
              $(targetdivid).text("Protch ! Check browser console");
              console.error(data)
            } else if(data["state"] == 'PENDING' || data["state"] == 'STARTED') {
              $(targetdivid).text("waiting..");
              setTimeout(poll, 1000)
            } else if(data["state"] == 'PROGRESS') {
              $(targetdivid).text("parsed " + data["completed"]["current"] + ' over ' + data["completed"]["total"] + ' categories');
              setTimeout(poll, 1000)
            } else if(data["state"] == 'SUCCESS') {
              $(targetdivid).text("parsed " + data["completed"] + " items, reloading page");
              window.location.reload();
            }
          })
      }
      poll();
    });
}

const FetchCswRecords = (portal) => {
  const targetdivid = '#progress';
  fetch(baseurl + '/tasks/fetchcswrecords/' + portal + '.json')
    .then(response => response.json())
    .then(mydata => {
      $(targetdivid).text("Queuing background task..");
      const poll = () => {
        fetch(baseurl + '/tasks/taskresults/' + mydata["taskid"])
          .then(response => response.json())
          .then(data => {
//            console.log(data)
            if (data === null) {
              $(targetdivid).text('got null, shouldnt happen ?');
            } else if (!data["state"] || data["state"] == 'FAILURE') {
              $(targetdivid).text("Protch ! Check browser console");
              console.error(data)
            } else if(data["state"] == 'PENDING' || data["state"] == 'STARTED') {
              $(targetdivid).text("waiting..");
              setTimeout(poll, 1000)
            } else if(data["state"] == 'PROGRESS') {
              $(targetdivid).text("fetched " + data["completed"]["current"] + ' over ' + data["completed"]["total"] + ' potential records');
              setTimeout(poll, 1000)
            } else if(data["state"] == 'SUCCESS') {
              $(targetdivid).text("successfully fetched " + data["completed"] + " records, reloading page");
              window.location.reload();
            }
          })
      }
      poll();
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
                  setTimeout(poll, 2000)
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
                            } else if (data['task'].includes('mviewer.check_all')) {
                              return {'url': j.args[0], 'xurl': baseurl + '/mviewer/' + j.args[0].replaceAll('/','~'), 'problem': GetPbStr(i) }
                            } else if (data['task'].includes('gsd.gsdatadir')) {
                            // gsdd
                              n = j.args[1].split('~')
                              if (n.length > 1) {
                                return {'url': n[n.length-1], 'xurl': baseurl + '/admin/geoserver/datadir/' + j.args[0].slice(0, -1) + '/' + j.args[1], 'problem': GetPbStr(i) }
                              } else {
                                return {'url': j.args[1], 'xurl': baseurl + '/admin/geoserver/datadir/' + j.args[0].slice(0, -1) + '/' + j.args[1], 'problem': GetPbStr(i) }
                              }
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
                      // if problems is undef, single task badly failed and returned the python exception as value
                      if (data["value"].problems !== undefined) {
                        const probs = data["value"].problems.map(i => {
                          return GetPbStr(i)
                        })
                        data["value"].problems = probs
                      }
                  }
                  if (data["value"].problems !== undefined && data["value"].problems.length > 0) {
                    if (!data["successful"]) {
                      /*
                       * try to figure out which job actually failed
                       * url member is a csw record identifier, or a wfs/wms layer name
                       * the last (args.at(-1)) job arg is also a csw record identifier or a wfs/wms layer name
                       * figure out which is missing from the list of returned jobs
                       */
                      const all = tableData.map(i => { return i.url });
                      const done = data["value"].map(i => { return i.args.at(-1) });
                      const missing = all.filter(x => !done.includes(x));
                      $(targetdivid).text("jobs on " + missing + " failed, did " + data["completed"] + " - on those, " + data["value"].problems.length + ' problems found');
                    } else {
                      $(targetdivid).text(data["value"].problems.length + ' problems found');
                    }
                    if (Array.isArray(data["value"])) {
                        var argtitle = 'Layer'
                        if (data['task'].includes('csw')) {
                          argtitle = 'Metadata'
                        } else if (data['task'].includes('check_resources')) {
                          argtitle = 'Map/Ctxid'
                        } else if (data['task'].includes('check_configs')) {
                          argtitle = 'Configfile'
                        } else if (data['task'].includes('mviewer.check_all')) {
                          argtitle = 'Config url'
                        } else if (data['task'].includes('gsd.gsdatadir')) {
                          argtitle = 'Item'
                        }
                        var prevexp = $(targetpbdivid + '-export')
                        if (prevexp.length > 0) {
                          prevexp.attr("href",baseurl + '/tasks/result/' + taskid)
                        } else {
                          const exportlink = $("<a>");
                          exportlink.attr("href",baseurl + '/tasks/result/' + taskid)
                          exportlink.attr("title","Export as JSON")
                          exportlink.attr("id",targetpbdivid.substring(1) + '-export')
                          exportlink.html('<p class="bi bi-filetype-json">View/Export problem list as JSON</p>');
                          $(targetpbdivid).append(exportlink)
                        }
                        var prevtable = $(targetpbdivid + '-table')
                        if (prevtable.length > 0) {
                          prevtable.bootstrapTable("load", data["value"].problems)
                        } else {
                          const pbta = $("<table>")
                          pbta.attr("id", targetpbdivid.substring(1) + '-table')
                          $(targetpbdivid).append(pbta)
                          pbta.bootstrapTable({
                            data: data["value"].problems,
                            search: true,
                            pagination: true,
                            columns: [
                              {'title': 'Index', 'formatter': 'runningFormatter'},
                              {'field': 'url', 'title': argtitle, 'sortable': true, 'formatter': 'urlFormatter'},
                              {'field': 'problem', 'title': 'Problem', 'sortable': true}
                            ]
                          });
                        }
                    } else {
                        $(targetpbdivid).html(ArrayToHtmlList(data["value"].problems));
                    }
                  } else {
                    if (!data["successful"]) {
                      if (data["completed"] !== undefined) {
                        $(targetdivid).text("some job failed, did " + data["completed"] + " - on those, found no errors");
                      } else {
                        $(targetdivid).text("job failed badly, raw error: " + data["value"]);
                      }
                    } else if (data["value"] === false) {
                        $(targetdivid).text("job failed early and didn't return a real value, check celery logs");
                    } else if (Array.isArray(data["value"]) && data["value"].length === 0 && data["finished"] === false && data["completed"] == "0 / 0") {
                        $(targetdivid).text("nothing to check ?");
                        return;
                    } else {
                      $(targetdivid).html('<a href="https://lessalesmajestes.bandcamp.com/album/no-problemo">No problemo!</a>')
                    }
                    $(targetpbdivid).empty();
                  }
                  const d = new Date(data["finished"] * 1000);
                  $(targetpbdetdivid).text('vérification faite le '+ d.toLocaleString("fr-FR"));
                  if ($(targetpreviousdivid).children().length == 0) {
                    $(targetpreviousdivid).html(ArrayToHtmlList([]));
                  }
                  if ($(targetpreviousdivid).find("#display-taskres-"+taskid).length == 0) {
                    const link = $("<a>");
                    link.attr("id", 'display-taskres-' + taskid)
                    link.attr("href","javascript:PollTaskRes('" + type +"','"+ resid + "','" + data['taskid'] + "'," + showdelete + ",'" + targetdivid + "');");
                    link.attr("title","Show result for task " + data["taskid"]);
                    link.text("check at " + d.toLocaleString("fr-FR"));
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
