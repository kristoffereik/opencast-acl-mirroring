# https://docs.opencast.org/develop/developer/#api/events-api/#get-apievents

import requests
import json
import sys
from requests.auth import HTTPBasicAuth

# auth = HTTPBasicAuth('admin', 'opencast')
# urlPrefix="https://stable.opencast.org/api/"
auth = HTTPBasicAuth('', '')
urlPrefix = "https://api.opencast.org/api/"


#######################################################################################################################
# ACL
#######################################################################################################################

def getSeriesACL(seriesID: str):
    return getACL(seriesID, series=True)


def getEventACL(eventID: str):
    return getACL(eventID, event=True)


def getACL(eventSeriesID: str, series: bool = False, event: bool = False):
    aclType = seriesEventChecker(series, event)
    urlSuffix = "{0}/{1}/acl".format(aclType, eventSeriesID)
    url = urlPrefix + urlSuffix
    resp = getResponse(url)
    return resp


def setACL(eventSeriesID: str, payload: dict, series: bool = False, event: bool = False):
    aclType = seriesEventChecker(series, event)
    urlSuffix = "{0}/{1}/acl".format(aclType, eventSeriesID)
    url = urlPrefix + urlSuffix
    r = requests.put(url, auth=auth, data=payload)
    return r.content


def ACLEntry(allow: bool, role: str, action: str):
    return [{'allow': allow, 'role': role, 'action': action}]


def ACLEntryLearner(role: str):
    role = role + "_Learner"
    action = "read"
    return ACLEntry(True, role, action)


def ACLEntryInstructor(role: str):
    role = role + "_Instructor"
    read = "read"
    write = "write"
    aclRead = ACLEntry(True, role, read).pop()
    aclWrite = ACLEntry(True, role, write).pop()
    aclList = [aclRead, aclWrite]
    return aclList


#######################################################################################################################
# Description
#######################################################################################################################

def getSeriesDescription(seriesID: str):
    return getDescription(seriesID, series=True)


def getEventDescription(eventID: str):
    return getDescription(eventID, event=True)


def getDescription(eventSeriesID: str, series: bool = False, event: bool = False):
    metadataType = seriesEventChecker(series, event)
    urlSuffix = "{0}/{1}/metadata".format(metadataType, eventSeriesID)
    url = urlPrefix + urlSuffix
    resp = getResponse(url)

    x = resp[0]["fields"]

    for elem in x:
        if elem["id"] == "description":
            return elem["value"]


#######################################################################################################################
# Workflows
#######################################################################################################################

def republishSingleMetadata(eventID: str):
    urlSuffix = "workflows"
    url = urlPrefix + urlSuffix
    payload = {"event_identifier": eventID, "workflow_definition_identifier": "republish-metadata"}
    r = requests.post(url, auth=auth, data=payload)
    json_str = json.dumps(r.json(), sort_keys=False, indent=0)
    return json_str


def republishMetadata(idList: list):
    for eventID in idList:
        republishSingleMetadata(eventID)


#######################################################################################################################
# Events
#######################################################################################################################

def getPublishedSeriesEvents(seriesID, allEvents: bool = False):
    eventIDs = []
    urlSuffix = "events?sort=title:DESC&limit=100&filter=is_part_of:{}".format(seriesID)
    url = urlPrefix + urlSuffix
    r = getResponse(url)

    for event in r:
        if allEvents:
            eventIDs.append(event["identifier"])
        else:
            if "engage-player" in event["publication_status"]:
                eventIDs.append(event["identifier"])

    return eventIDs


#######################################################################################################################
# General functions
#######################################################################################################################

def mirrorSeries(idFrom: str, idTo: str):
    acl_From = getSeriesACL(idFrom)
    desc = getSeriesDescription(idTo)

    aclLearner = ACLEntryLearner(desc)
    aclInstructor = ACLEntryInstructor(desc)
    mergedACL = acl_From + aclLearner + aclInstructor
    load = {"acl": json.dumps(mergedACL)}
    setACL(idFrom, load, series=True)

    eventIDsFrom = getPublishedSeriesEvents(idFrom, allEvents=True)
    nAll = len(eventIDsFrom)

    for eventID in eventIDsFrom:
        eventACL = getEventACL(eventID)
        mergedACL = eventACL + aclLearner + aclInstructor
        load = {"acl": json.dumps(mergedACL)}
        setACL(eventID, load, event=True)

    eventIDsFrom = getPublishedSeriesEvents(idFrom)
    nRepublish = len(eventIDsFrom)
    workDone = {"aclChanges": nAll, "republished": nRepublish}
    republishMetadata(eventIDsFrom)
    return workDone

def seriesSearch(searchTerm:str, searchFrom:bool=False, searchTo:bool=False):
    seriesIDs = {}
    urlSearch = "series?filter=textFilter:{}&sort=title:ASC&limit=100"
    seriesEventChecker(searchFrom, searchTo)

    urlSuffix = urlSearch.format(searchTerm)
    url = urlPrefix + urlSuffix
    seriesSearch = getResponse(url)

    for index, series in enumerate(seriesSearch):
        seriesIDs[index] = series["identifier"]
        print("Nr.", index, "-", series["title"], " - ", series["identifier"])

    indexFrom = int(input("Velg nr.: "))
    seriesID = seriesIDs[indexFrom]
    return seriesID


def seriesSearchFrom():
    searchSeries = input("Søk etter emne som skal kopieres fra: ")
    return seriesSearch(searchSeries, searchFrom=True)


def seriesSearchTo():
    searchSeries = input("Søk etter emne som skal kopieres fra: ")
    return seriesSearch(searchSeries, searchTo=True)

def seriesEventChecker(series: bool, event: bool):
    # todo: make more general
    metadataType = None
    if not (series or event):
        raise Exception("No True values detected")
    if series and event:
        raise Exception("More than one True value detected")
    if series:
        metadataType = "series"
    if event:
        metadataType = "events"
    return metadataType


def getResponse(url: str):
    r = requests.get(url, auth=auth)
    json_str = json.dumps(r.json(), sort_keys=False, indent=0)
    resp = json.loads(json_str)
    return resp


#######################################################################################################################
# Main
#######################################################################################################################

def main():
    if len(sys.argv) > 1:
        idFrom = sys.argv[1]
        idTo = sys.argv[2]
        mirrorSeries(idFrom, idTo)
    else:
        idFrom = seriesSearchFrom()
        idTo = seriesSearchTo()
        print("Arbeider...")
        workDone = mirrorSeries(idFrom, idTo)
        nACLChanges = workDone["aclChanges"]
        nRepublishingMetadata = workDone["republished"]
        print("Endret ACL for {} opptak og republiserer metadata for {} opptak.".format(nACLChanges,
                                                                                       nRepublishingMetadata))


if __name__ == "__main__":
    main()