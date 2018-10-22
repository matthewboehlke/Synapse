#!/usr/bin/env python3
# -*- coding: utf8 -*-

import logging
import json

from thehive4py.api import TheHiveApi
from thehive4py.models import Case, CaseTask, CaseTaskLog, CaseObservable

class TheHiveConnector:
    'TheHive connector'

    def __init__(self, cfg):
        self.logger = logging.getLogger('workflows.' + __name__)
        self.cfg = cfg

        self.theHiveApi = self.connect()

    def connect(self):
        self.logger.info('%s.connect starts', __name__)

        url = self.cfg.get('TheHive', 'url')
        api_key = self.cfg.get('TheHive', 'api_key')

        return TheHiveApi(url, api_key)

    def searchCaseByDescription(self, string):
        #search case with a specific string in description
        #returns the ES case ID

        self.logger.info('%s.searchCaseByDescription starts', __name__)

        query = dict()
        query['_string'] = 'description:"{}"'.format(string)
        range = 'all'
        sort = []
        response = self.theHiveApi.find_cases(query=query, range=range, sort=sort)

        if response.status_code != 200:
            error = dict()
            error['message'] = 'search case failed'
            error['query'] = query
            error['payload'] = response.json()
            self.logger.error('Query to TheHive API did not return 200')
            raise ValueError(json.dumps(error, indent=4, sort_keys=True))

        if len(response.json()) == 1:
            #one case matched
            esCaseId = response.json()[0]['id']
            return esCaseId
        elif len(response.json()) == 0:
            #no case matched
            return None
        else:
            #unknown use case
            raise ValueError('unknown use case after searching case by description')


    def craftCase(self, title, description, **attributes):
        self.logger.info('%s.craftCase starts', __name__)

        _tags = ['Synapse']
        tags = attributes.get('tags',False)
        if tags:
            for tag in tags:
                _tags.append(tag)

        case = Case(title=title,
            tlp=2,
            tags=['Synapse'],
            description=description,
            tlp=attributes.get('tlp',2),
            severity=attributes.get('severity',2),
            flag=attributes.get('flag',False),
            tags=_tags,
            template=attributes.get('tamplate',None)
            )

        return case

    def createCase(self, case):
        self.logger.info('%s.createCase starts', __name__)

        response = self.theHiveApi.create_case(case)

        if response.status_code == 201:
            esCaseId =  response.json()['id']
            createdCase = self.theHiveApi.case(esCaseId)
            return createdCase
        else:
            self.logger.error('Case creation failed')
            raise ValueError(json.dumps(response.json(), indent=4, sort_keys=True))

    def assignCase(self, case, assignee):
        self.logger.info('%s.assignCase starts', __name__)

        esCaseId = case.id
        case.owner = assignee
        self.theHiveApi.update_case(case)

        updatedCase = self.theHiveApi.case(esCaseId)
        return updatedCase

    def craftCommTask(self):
        self.logger.info('%s.craftCommTask starts', __name__)

        commTask = CaseTask(title='Communication',
            status='InProgress',
            owner='synapse')

        return commTask

    def createTask(self, esCaseId, task):
        self.logger.info('%s.createTask starts', __name__)

        response = self.theHiveApi.create_case_task(esCaseId, task)

        if response.status_code == 201:
            esCreatedTaskId = response.json()['id']
            return esCreatedTaskId
        else:
            self.logger.error('Task creation failed')
            raise ValueError(json.dumps(response.json(), indent=4, sort_keys=True))

    def craftTaskLog(self, textLog):
        self.logger.info('%s.craftTaskLog starts', __name__)

        log = CaseTaskLog(message=textLog)

        return log

    def addTaskLog(self, esTaskId, textLog):
        self.logger.info('%s.addTaskLog starts', __name__)

        response = self.theHiveApi.create_task_log(esTaskId, textLog)

        if response.status_code == 201:
            esCreatedTaskLogId = response.json()['id']
            return esCreatedTaskLogId
        else:
            self.logger.error('Task log creation failed')
            raise ValueError(json.dumps(response.json(), indent=4, sort_keys=True))

    def getTaskIdByTitle(self, esCaseId, taskTitle):
        self.logger.info('%s.getTaskIdByName starts', __name__)

        response = self.theHiveApi.get_case_tasks(esCaseId)
        for task in response.json():
            if task['title'] == taskTitle:
                return task['id']

        #no <taskTitle> found
        return None

    def addFileObservable(self, esCaseId, filepath, comment):
        self.logger.info('%s.addFileObservable starts', __name__)

        file_observable = CaseObservable(dataType='file',
            data=[filepath],
            tlp=2,
            ioc=False,
            tags=['Synapse'],
            message=comment
        )

        response = self.theHiveApi.create_case_observable(
            esCaseId, file_observable)

        if response.status_code == 201:
            esObservableId = response.json()['id']
            return esObservableId
        else:
            self.logger.error('File observable upload failed')
            raise ValueError(json.dumps(response.json(), indent=4, sort_keys=True))
