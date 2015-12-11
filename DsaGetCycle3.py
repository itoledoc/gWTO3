import os
import sys
from DsaXmlParsers3 import *
import shutil

__author__ = 'itoledo'

prj = '{Alma/ObsPrep/ObsProject}'
val = '{Alma/ValueTypes}'
sbl = '{Alma/ObsPrep/SchedBlock}'


def get_all_apdm(cursor, data_path, obsproject_uids, phasei):

    try:
        os.mkdir(data_path)
        os.mkdir(data_path + 'obsproject')
        os.mkdir(data_path + 'obsreview')
        os.mkdir(data_path + 'obsproposal')
        os.mkdir(data_path + 'schedblock')
    except OSError:
        shutil.rmtree(data_path)
        os.mkdir(data_path)
        os.mkdir(data_path + 'obsproject')
        os.mkdir(data_path + 'obsreview')
        os.mkdir(data_path + 'obsproposal')
        os.mkdir(data_path + 'schedblock')

    projects = len(obsproject_uids)
    c = 1
    for uid in obsproject_uids:

        sys.stdout.write("Downloading Project number %d of %d \r" % (
            c, projects))
        sys.stdout.flush()

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
        c += 1

    num = len(os.listdir(data_path + 'obsproject'))
    c = 1
    for r in os.listdir(data_path + 'obsproject'):
        sys.stdout.write("Downloading Review/Proposal [%d%%]          \r" % (
            100 * c / num))
        sys.stdout.flush()
        c += 1
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
                xmlfilename = obspropuid.replace(
                    '://', '___').replace('/', '_') + \
                    '.xml'
                filename = data_path + 'obsproposal/' + xmlfilename
                io_file = open(filename, 'w')
                io_file.write(xml_content)
                io_file.close()
            except IndexError:
                print("Proposal %s not found on archive?" %
                      obspropuid)

            try:
                obsrevuid = obsparse.data.ObsReviewRef.attrib['entityId']
            except AttributeError:
                # print("Obsproject %s has no ObsReviewRef" % r)
                continue

            cursor.execute(
                "SELECT TIMESTAMP, XMLTYPE.getClobVal(xml) "
                "FROM ALMA.XML_OBSREVIEW_ENTITIES "
                "WHERE ARCHIVE_UID = '%s'" % obsrevuid)

            try:
                data = cursor.fetchall()[0]
                xml_content = data[1].read()
                xmlfilename = obsrevuid.replace(
                    '://', '___').replace('/', '_') + \
                    '.xml'
                filename = data_path + 'obsreview/' + xmlfilename
                io_file = open(filename, 'w')
                io_file.write(xml_content)
                io_file.close()
            except IndexError:
                print("Review %s not found on archive?" %
                      obsrevuid)
                continue

    num = len(os.listdir(data_path + 'obsreview/'))
    c = 1
    for r in os.listdir(data_path + 'obsreview/'):
        if not r.startswith('uid'):
            c += 1
            continue

        sys.stdout.write("Downloading Phase1 SBs [%d%%]          \r" % (
            100 * c / num))
        sys.stdout.flush()

        obsreview = ObsReview(r,
                              path=data_path + 'obsreview/')
        if obsreview.data.ObsProjectRef.attrib['entityId'] not in phasei:
            # print("%s is phase II!" %
            #       obsreview.data.ObsProjectRef.attrib['entityId'])
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
                xmlfilename = sbuid.replace('://', '___').replace('/', '_') + \
                    '.xml'
                filename = data_path + 'schedblock/' + \
                    xmlfilename
                io_file = open(filename, 'w')
                io_file.write(xml_content)
                io_file.close()
            except IndexError:
                print("SB %s not found on archive?" % sbuid)
                c += 1
                continue
        c += 1

    num = len(os.listdir(data_path + 'obsproject/'))
    c = 1
    for r in os.listdir(data_path + 'obsproject/'):
        sys.stdout.write("Downloading Phase2 SBs [%d%%]          \r" % (
            100 * c / num))
        sys.stdout.flush()
        c += 1
        if not r.startswith('uid'):
            continue
        obsparse = ObsProject(
            r, path=data_path + 'obsproject/')
        obspropuid = obsparse.data.ObsProjectEntity.attrib['entityId']
        if obspropuid in obsproject_uids:
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
                    xmlfilename = sbuid.replace(
                        '://', '___').replace('/', '_') + \
                        '.xml'
                    filename = data_path + 'schedblock/' + xmlfilename
                    io_file = open(filename, 'w')
                    io_file.write(xml_content)
                    io_file.close()
                except IndexError:
                    print("SB %s not found on archive?" % sbuid)
                    continue


def get_apdm(cursor, data_path, obsproject_uid):

    uidxml = obsproject_uid.replace('://', '___').replace('/', '_') + '.xml'
    print uidxml, obsproject_uid

    cursor.execute(
        "SELECT TIMESTAMP, XMLTYPE.getClobVal(xml) "
        "FROM ALMA.XML_OBSPROJECT_ENTITIES "
        "WHERE ARCHIVE_UID = '%s'" % obsproject_uid)
    try:
        data = cursor.fetchall()[0]
        xml_content = data[1].read()
        filename = data_path + 'obsproject/' + uidxml
        io_file = open(filename, 'w')
        io_file.write(xml_content)
        io_file.close()
    except IndexError:
        print("Project %s not found on archive?" % obsproject_uid)
    except IOError:
        print("Project %s not found on archive?" % obsproject_uid)

    obsparse = ObsProject(
        uidxml, path=data_path + 'obsproject/')
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
        filename = data_path + 'obsproposal/' + xmlfilename
        io_file = open(filename, 'w')
        io_file.write(xml_content)
        io_file.close()
    except IndexError:
        print("Proposal %s not found on archive?" %
              obspropuid)

    try:
        obsrevuid = obsparse.data.ObsReviewRef.attrib['entityId']
        cursor.execute(
            "SELECT TIMESTAMP, XMLTYPE.getClobVal(xml) "
            "FROM ALMA.XML_OBSREVIEW_ENTITIES "
            "WHERE ARCHIVE_UID = '%s'" % obsrevuid)
        try:
            data = cursor.fetchall()[0]
            xml_content = data[1].read()
            xmlfilename = obsrevuid.replace('://', '___').replace('/', '_') + \
                '.xml'
            filename = data_path + 'obsreview/' + xmlfilename
            io_file = open(filename, 'w')
            io_file.write(xml_content)
            io_file.close()
        except IndexError:
            print("Review %s not found on archive?" %
                  obsrevuid)
    except AttributeError:
        print("Obsproject %s has no ObsReviewRef" % obsproject_uid)

    obsparse = ObsProject(
        uidxml, path=data_path + 'obsproject/')
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
            filename = data_path + 'schedblock/' + xmlfilename
            io_file = open(filename, 'w')
            io_file.write(xml_content)
            io_file.close()
        except IndexError:
            print("SB %s not found on archive?" % sbuid)
            continue

    return uidxml
