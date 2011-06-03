###############################################################################
##
## Copyright (C) 2006-2011, University of Utah. 
## All rights reserved.
## Contact: vistrails@sci.utah.edu
##
## This file is part of VisTrails.
##
## "Redistribution and use in source and binary forms, with or without 
## modification, are permitted provided that the following conditions are met:
##
##  - Redistributions of source code must retain the above copyright notice, 
##    this list of conditions and the following disclaimer.
##  - Redistributions in binary form must reproduce the above copyright 
##    notice, this list of conditions and the following disclaimer in the 
##    documentation and/or other materials provided with the distribution.
##  - Neither the name of the University of Utah nor the names of its 
##    contributors may be used to endorse or promote products derived from 
##    this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
## AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
## THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
## PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
## EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
## PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
## OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
## WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
## OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
###############################################################################
from PyQt4 import QtGui
from PyQt4.QtCore import QString
from core.thumbnails import ThumbnailCache
import xml.sax.saxutils
import urlparse

from entity import Entity
from workflow import WorkflowEntity
from workflow_exec import WorkflowExecEntity
from thumbnail import ThumbnailEntity

class VistrailEntity(Entity):
    type_id = 1

    def __init__(self, vistrail=None):
        Entity.__init__(self)
        self.id = None
        self.update(vistrail)

    @staticmethod
    def load(*args):
        entity = VistrailEntity()
        Entity.load(entity, *args)
        return entity
    
    def create_workflow_entity(self, workflow, action):
        entity = WorkflowEntity(workflow)
        self.children.append(entity)
        if self.vistrail.has_notes(action.id):
            notes = xml.sax.saxutils.unescape(self.vistrail.get_notes(action.id))
            fragment = QtGui.QTextDocumentFragment.fromHtml(QString(notes))
            plain_notes = str(fragment.toPlainText())
            entity.description = plain_notes
        else:
            entity.description = ''
        entity.user = action.user
        entity.mod_time = action.date
        entity.create_time = action.date
        scheme, rest = self.url.split('://', 1)
        url = 'http://' + rest
        url_tuple = urlparse.urlsplit(url)
        query_str = url_tuple[3]
        if query_str == '':
            query_str = 'workflow=%s' % action.id
        else:
            query_str += '&workflow=%s' % action.id
        url_tuple = (scheme, url_tuple[1], url_tuple[2], query_str,
                     url_tuple[4])
        entity.url = urlparse.urlunsplit(url_tuple)
        # entity.url = self.url + '?workflow_id=%s' % action.id
        return entity

    def update(self, vistrail):
        self.vistrail = vistrail
        if self.vistrail is not None:
            wf_entity_map = {}
            latestVersion = self.vistrail.actionMap[self.vistrail.get_latest_version()]
            firstVersion = self.vistrail.actionMap[1] \
                if 1 in self.vistrail.actionMap else latestVersion


            self.name = self.vistrail.locator.short_name
            if not self.name or self.name == 'None':
                self.name = self.vistrail.db_name
            self.user = latestVersion.user
            self.mod_time = latestVersion.date
            self.create_time = firstVersion.date
            self.size = len(self.vistrail.actionMap)
            self.description = ""
            self.url = self.vistrail.locator.to_url()
            self.was_updated = True

            for id, tag in self.vistrail.get_tagMap().iteritems():
                if id not in self.vistrail.actionMap:
                    continue
                action = self.vistrail.actionMap[id]
                workflow = self.vistrail.getPipeline(id)
                tag = self.vistrail.get_action_annotation(id, "__tag__")
                if tag:
                    workflow.name = tag.value
                # if workflow already exists, we want to update it...
                # spin through self.children and look for matching
                # workflow entity?
                # self.children.append(WorkflowEntity(workflow))
                wf_entity_map[id] = \
                    self.create_workflow_entity(workflow, action)

            log = vistrail.get_log()
            if log is not None:
                for wf_exec in log.workflow_execs:
                    version_id = wf_exec.parent_version
                    if version_id not in wf_entity_map:

                        # FIXME add new workflow entity for this version
                        if version_id not in self.vistrail.actionMap:
                            continue
                        action = self.vistrail.actionMap[version_id]
                        workflow = self.vistrail.getPipeline(version_id)
                        wf_entity = \
                            self.create_workflow_entity(workflow, action)

                        wf_entity_map[version_id] = wf_entity
                    else:
                        wf_entity = wf_entity_map[version_id]
                    entity = WorkflowExecEntity(wf_exec)

                    scheme, rest = self.url.split('://', 1)
                    url = 'http://' + rest
                    url_tuple = urlparse.urlsplit(url)
                    query_str = url_tuple[3]
                    if query_str == '':
                        query_str = 'workflow_exec=%s' % entity.name
                    else:
                        query_str += '&workflow_exec=%s' % entity.name
                    url_tuple = (scheme, url_tuple[1], url_tuple[2], query_str,
                                 url_tuple[4])
                    entity.url = urlparse.urlunsplit(url_tuple)
                    wf_entity.children.append(entity)

            for action in self.vistrail.actionMap.itervalues():
                thumbnail = self.vistrail.get_thumbnail(action.id)
                if thumbnail is not None:
                    cache = ThumbnailCache.getInstance()
                    path = cache.get_abs_name_entry(thumbnail)
                    if not path:
                        continue
                    entity = ThumbnailEntity(path)

                    if action.id in wf_entity_map:
                        wf_entity_map[action.id].children.append(entity)
                    else:
                        # there is a thumbnail but the action is not important
                        #print "No such action:", action.id                    
                        pass

#     # returns string
#     def get_name(self):
#         return self.vistrail.name
    
#     # returns datetime
#     def get_mod_time(self):
#         return self.vistrail.get_most_recent_action().py_date

#     # returns datetime
#     def get_create_time(self):
#         return self.vistrail.get_first_action().py_date
    
#     # returns string
#     # FIXME: perhaps this should be a User object at some point
#     def get_user(self):
#         return self.vistrail.get_most_recent_action().py_date
    
#     # returns tuple (<entity_type>, <entity_id>)
#     def get_id(self):
#         return (self.vistrail.vtType, self.vistrail.id)

#     # returns integer
#     def get_size(self):
#         return len(self.vistrail.actionMap)
    
#     # returns possibly empty list of Entity objects
#     def get_children(self):
#         return len(self.vistrail.tagMap)

#     # returns list of strings representing paths
#     # FIXME: should this be urls for database access?
#     def get_image_fnames(self):
#         return []
    
    # returns boolean, True if search input is satisfied else False
    def match(self, search):
        # try match on self
        

        # if no match on self, check for a match on all children
        for child in self.get_children():
            if child.match(search):
                return True

    def open(self):
        locator = BaseLocator.from_url(self.url)
        locator._name = self.name
        core.open_locator(locator)
