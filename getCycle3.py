import os
import cx_Oracle
from XmlParsers3 import *
import shutil

__author__ = 'itoledo'

prj = '{Alma/ObsPrep/ObsProject}'
val = '{Alma/ValueTypes}'
sbl = '{Alma/ObsPrep/SchedBlock}'

pd.options.display.width = 200
pd.options.display.max_columns = 100

# get Cycle3 APDM

conx_string = os.environ['CON_STR']
connection = cx_Oracle.connect(conx_string)
cursor = connection.cursor()

path = os.environ['PHASEONE_C3']
data_path = os.environ['PHASEONE_C3']

sql1 = str(
    "SELECT obs1.PRJ_ARCHIVE_UID as OBSPROJECT_UID, obs1.PI, "
    "obs1.PRJ_NAME,"
    "CODE,PRJ_SCIENTIFIC_RANK,PRJ_VERSION,"
    "PRJ_LETTER_GRADE,DOMAIN_ENTITY_STATE as PRJ_STATUS,"
    "obs3.ARCHIVE_UID as OBSPROPOSAL_UID, obs4.DC_LETTER_GRADE,"
    "obs3.CYCLE "
    "FROM ALMA.BMMV_OBSPROJECT obs1, ALMA.OBS_PROJECT_STATUS obs2,"
    " ALMA.BMMV_OBSPROPOSAL obs3, ALMA.PROPOSAL obs4 "
    "WHERE regexp_like (CODE, '^201[35]\..*\.[AST]') "
    "AND obs2.OBS_PROJECT_ID = obs1.PRJ_ARCHIVE_UID AND "
    "obs1.PRJ_ARCHIVE_UID = obs3.PROJECTUID AND "
    "obs4.ARCHIVE_UID = obs3.ARCHIVE_UID AND "
    "obs4.DC_LETTER_GRADE IN ('A', 'B', 'C')")

cursor.execute(sql1)

df1 = pd.DataFrame(
    cursor.fetchall(), columns=[rec[0] for rec in cursor.description])

df1 = df1.query(
    '((CYCLE in ["2015.1", "2015.A"]) or '
    '(CYCLE in ["2013.1", "2013.A"] and DC_LETTER_GRADE == "A")) and '
    'PRJ_STATUS != "Canceled"').copy()

obsproject_uids = df1.OBSPROJECT_UID.unique()
phase2 = df1.query(
    'PRJ_STATUS not in ["Phase1Submitted", "Rejected", "Approved"]'
).OBSPROJECT_UID.unique()

try:
    os.mkdir(path)
    os.mkdir(path + 'obsproject')
    os.mkdir(path + 'obsreview')
    os.mkdir(path + 'obsproposal')
    os.mkdir(path + 'schedblock')
except OSError:
    shutil.rmtree(path)
    os.mkdir(path)
    os.mkdir(path + 'obsproject')
    os.mkdir(path + 'obsreview')
    os.mkdir(path + 'obsproposal')
    os.mkdir(path + 'schedblock')

for uid in obsproject_uids:
    cursor.execute(
        "SELECT TIMESTAMP, XMLTYPE.getClobVal(xml) "
        "FROM ALMA.XML_OBSPROJECT_ENTITIES "
        "WHERE ARCHIVE_UID = '%s'" % uid)
    try:
        data = cursor.fetchall()[0]
        xml_content = data[1].read()
        xmlfilename = uid.replace('://', '___').replace('/', '_') + '.xml'
        filename = data_path + 'obsproject/' + xmlfilename
        io_file = open(filename, 'w')
        io_file.write(xml_content)
        io_file.close()
    except IndexError:
        print("Project %s not found on archive?" % uid)
    except IOError:
        print("Project %s not found on archive?" % uid)

for r in os.listdir(data_path + 'obsproject'):
    if r.startswith('uid'):
        obsparse = ObsProject(
            r, path=data_path + 'obsproject/')
        obspropuid = obsparse.data.ObsProposalRef.attrib['entityId']

        cursor.execute(
            "SELECT TIMESTAMP, XMLTYPE.getClobVal(xml) "
            "FROM ALMA.XML_OBSPROPOSAL_ENTITIES "
            "WHERE ARCHIVE_UID = '%s'" % obspropuid)

        try:
            data = cursor.fetchall()[0]
            xml_content = data[1].read()
            xmlfilename = obspropuid.replace('://', '___').replace('/', '_') + \
                '.xml'
            filename = data_path + 'obsproposal/' + \
                       xmlfilename
            io_file = open(filename, 'w')
            io_file.write(xml_content)
            io_file.close()
        except IndexError:
            print("Proposal %s not found on archive?" %
                  obspropuid)

        try:
            obsrevuid = obsparse.data.ObsReviewRef.attrib['entityId']
        except AttributeError:
            print("Obsproject %s has no ObsReviewRef" % r)
            continue

        cursor.execute(
            "SELECT TIMESTAMP, XMLTYPE.getClobVal(xml) "
            "FROM ALMA.XML_OBSPROPOSAL_ENTITIES "
            "WHERE ARCHIVE_UID = '%s'" % obspropuid)

        try:
            data = cursor.fetchall()[0]
            xml_content = data[1].read()
            xmlfilename = obspropuid.replace('://', '___').replace('/', '_') + \
                '.xml'
            filename = data_path + 'obsproposal/' + \
                       xmlfilename
            io_file = open(filename, 'w')
            io_file.write(xml_content)
            io_file.close()
        except IndexError:
            print("Proposal %s not found on archive?" %
                  obspropuid)
            continue

        cursor.execute(
            "SELECT TIMESTAMP, XMLTYPE.getClobVal(xml) "
            "FROM ALMA.XML_OBSREVIEW_ENTITIES "
            "WHERE ARCHIVE_UID = '%s'" % obsrevuid)

        try:
            data = cursor.fetchall()[0]
            xml_content = data[1].read()
            xmlfilename = obsrevuid.replace('://', '___').replace('/', '_') + \
                '.xml'
            filename = data_path + 'obsreview/' + \
                       xmlfilename
            io_file = open(filename, 'w')
            io_file.write(xml_content)
            io_file.close()
        except IndexError:
            print("Review %s not found on archive?" %
                  obsrevuid)
            continue


for r in os.listdir(data_path + 'obsreview/'):
    if not r.startswith('uid'):
        continue
    obsreview = ObsReview(r,
                          path=data_path + 'obsreview/')
    if obsreview.data.ObsProjectRef.attrib['entityId'] in phase2:
        print("%s is phase II!" %
              obsreview.data.ObsProjectRef.attrib['entityId'])
        continue
    op = obsreview.data.findall('.//' + prj + 'SchedBlockRef')
    for sbref in op:
        sbuid = sbref.attrib['entityId']
        cursor.execute(
            "SELECT TIMESTAMP, XMLTYPE.getClobVal(xml) "
            "FROM ALMA.XML_SCHEDBLOCK_ENTITIES "
            "WHERE ARCHIVE_UID = '%s'" % sbuid)
        try:
            data = cursor.fetchall()[0]
            xml_content = data[1].read()
            xmlfilename = sbuid.replace('://', '___').replace('/', '_') + '.xml'
            filename = data_path + 'schedblock/' + \
                       xmlfilename
            io_file = open(filename, 'w')
            io_file.write(xml_content)
            io_file.close()
        except IndexError:
            print("SB %s not found on archive?" % sbuid)
            continue

for r in os.listdir(data_path + 'obsproject/'):
    if not r.startswith('uid'):
        continue
    obsparse = ObsProject(
        r, path=data_path + 'obsproject/')
    obspropuid = obsparse.data.ObsProjectEntity.attrib['entityId']
    if obspropuid in phase2:
        op = obsparse.data.ObsProgram.findall('.//' + prj + 'SchedBlockRef')
        for sbref in op:
            sbuid = sbref.attrib['entityId']
            cursor.execute(
                "SELECT TIMESTAMP, XMLTYPE.getClobVal(xml) "
                "FROM ALMA.XML_SCHEDBLOCK_ENTITIES "
                "WHERE ARCHIVE_UID = '%s'" % sbuid)
            try:
                data = cursor.fetchall()[0]
                xml_content = data[1].read()
                xmlfilename = sbuid.replace('://', '___').replace('/', '_') + \
                    '.xml'
                filename = data_path + 'schedblock/' + \
                           xmlfilename
                io_file = open(filename, 'w')
                io_file.write(xml_content)
                io_file.close()
            except IndexError:
                print("SB %s not found on archive?" % sbuid)
                continue
