from lxml import objectify
import pandas as pd
from WtoConverter3 import *
import ephem

__author__ = 'itoledo'


prj = '{Alma/ObsPrep/ObsProject}'
val = '{Alma/ValueTypes}'
sbl = '{Alma/ObsPrep/SchedBlock}'


# noinspection PyBroadException
class ObsProposal(object):

    def __init__(self, xml_file, obsproject_uid, path='./'):
        """

        :param xml_file:
        :param path:
        """
        io_file = open(path + xml_file)
        tree = objectify.parse(io_file)
        io_file.close()
        self.obsproject_uid = obsproject_uid
        self.data = tree.getroot()

        self.sg_targets = []
        self.sciencegoals = []
        self.visits = []
        self.temp_param = []
        self.sg_specwindows = []
        self.sg_specscan = []

    def get_sg(self):
        sg_list = self.data.findall(prj + 'ScienceGoal')
        c = 1
        for sg in sg_list:
            self.read_ph1_sg(sg, str("%02d" % c))
            c += 1

    def read_ph1_sg(self, sg, idnum):
        sg_id = self.obsproject_uid + '_' + str(idnum)

        # Handle exceptions of Science Goals without ObsUnitSets or SchedBlocks
        try:
            # ous_id = the id of associated ObsUnitSet at the ObsProgram level.
            ous_id = sg.ObsUnitSetRef.attrib['partId']
            hassb = True
        except AttributeError:
            ous_id = None
            hassb = False

        # get SG name, bands and estimated time
        sg_name = sg.name.pyval
        try:
            sg_mode = sg.attrib['mode']
        except KeyError:
            # print sg_id
            sg_mode = None
        bands = sg.findall(prj + 'requiredReceiverBands')[0].pyval
        estimatedtime = convert_tsec(
            sg.estimatedTotalTime.pyval,
            sg.estimatedTotalTime.attrib['unit']) / 3600.

        # get SG's AR (in arcsec), LAS (arcsec), sensitivity (Jy), useACA and
        # useTP
        performance = sg.PerformanceParameters
        ar = convert_sec(
            performance.desiredAngularResolution.pyval,
            performance.desiredAngularResolution.attrib['unit'])
        las = convert_sec(
            performance.desiredLargestScale.pyval,
            performance.desiredLargestScale.attrib['unit'])
        sensitivity = convert_jy(
            performance.desiredSensitivity.pyval,
            performance.desiredSensitivity.attrib['unit'])
        useaca = performance.useACA.pyval
        usetp = performance.useTP.pyval
        ispointsource = performance.isPointSource.pyval

        # Check if it is a TimeConstrained SG
        try:
            istimeconstrained = performance.isTimeConstrained.pyval
        except AttributeError:
            istimeconstrained = None

        if istimeconstrained:
            try:
                visit = performance.VisitConstraint
                for v in visit:
                    try:
                        starttime = v.startTime.pyval
                    except AttributeError:
                        starttime = None
                    try:
                        allowedmargin = v.allowedMargin.pyval
                        allowedmargin_unit = v.allowedMargin.attrib['unit']
                    except AttributeError:
                        allowedmargin = None
                        allowedmargin_unit = None
                    try:
                        note = v.note.pyval
                    except:
                        note = None
                    isavoidconstraint = v.isAvoidConstraint.pyval
                    priority = v.priority.pyval
                    try:
                        isfixedstart = v.isFixedStart.pyval
                    except AttributeError:
                        isfixedstart = None

                    visitid = v.visitId.pyval
                    prev_visitid = v.previousVisitId.pyval
                    try:
                        requireddelay = v.requiredDelay.pyval
                        requireddelay_unit = v.requiredDelay.attrib['unit']
                    except:
                        requireddelay = None
                        requireddelay_unit = None
                    self.visits.append([
                        sg_id, sg_name, self.obsproject_uid,
                        starttime, allowedmargin, allowedmargin_unit, note,
                        isavoidconstraint, priority, visitid, prev_visitid,
                        requireddelay, requireddelay_unit, isfixedstart])
            except AttributeError:
                try:
                    temp = performance.TemporalParameters
                except AttributeError:
                    temp = performance.MonitoringConstraint
                for t in temp:
                    starttime = t.startTime.pyval
                    try:
                        endtime = t.endTime.pyval
                    except AttributeError:
                        endtime = None
                    allowedmargin = t.allowedMargin.pyval
                    allowedmargin_unit = t.allowedMargin.attrib['unit']
                    try:
                        repeats = t.repeats.pyval
                    except AttributeError:
                        repeats = None
                    try:
                        lstmin = t.lSTMin.pyval
                        lstmax = t.lSTMax.pyval
                    except:
                        lstmin = None
                        lstmax = None
                    try:
                        note = t.note.pyval
                    except:
                        note = None
                    isavoidconstraint = t.isAvoidConstraint.pyval
                    priority = t.priority.pyval
                    fixedstart = t.isFixedStart.pyval
                    self.temp_param.append([
                        sg_id, sg_name, self.obsproject_uid,
                        starttime, endtime, allowedmargin, allowedmargin_unit,
                        repeats, lstmin, lstmax, note, isavoidconstraint,
                        priority, fixedstart
                    ])

        # Get SG representative Frequency, polarization configuration.
        calparam = sg.CalibrationSetupParameters
        calspecial = False
        if calparam.attrib['selection'] == 'user':
            calspecial = True

        spectral = sg.SpectralSetupParameters
        repfreq = convert_ghz(
            performance.representativeFrequency.pyval,
            performance.representativeFrequency.attrib['unit'])
        repfreq_spec = convert_ghz(
            spectral.representativeFrequency.pyval,
            spectral.representativeFrequency.attrib['unit'])

        polarization = spectral.attrib['polarisation']
        type_pol = spectral.attrib['type']
        specscan = spectral.findall(prj + 'SpectralScan')
        try:
            singlecont_freq = convert_ghz(
                spectral.singleContinuumFrequency.pyval,
                spectral.singleContinuumFrequency.attrib['unit']
            )
        except:
            singlecont_freq = None

        spw = spectral.findall(prj + 'ScienceSpectralWindow')
        is_spec_scan = False
        if len(specscan) > 0:
            is_spec_scan = True
            for n in range(len(specscan)):
                ss = specscan[n]
                ss_index = ss['index'].pyval
                startfrequency = convert_ghz(
                    ss.startFrequency.pyval,
                    ss.startFrequency.attrib['unit'])
                endfrequency = convert_ghz(
                    ss.endFrequency.pyval,
                    ss.endFrequency.attrib['unit'])
                bandwidth = convert_ghz(
                    ss.bandWidth.pyval,
                    ss.bandWidth.attrib['unit']
                )
                specres = convert_ghz(
                    ss.spectralResolution.pyval,
                    ss.spectralResolution.attrib['unit']
                )
                isskyfreq = ss.isSkyFrequency.pyval

                self.sg_specscan.append([
                    sg_id, ss_index, startfrequency, endfrequency,
                    bandwidth, specres, isskyfreq
                ])

        else:
            for n in range(len(spw)):
                sp = spw[n]
                spw_index = sp['index'].pyval
                transition_name = sp.transitionName.pyval
                centerfrequency = convert_ghz(
                    sp.centerFrequency.pyval,
                    sp.centerFrequency.attrib['unit']
                )
                bandwidth = convert_ghz(
                    sp.bandWidth.pyval,
                    sp.bandWidth.attrib['unit']
                )
                spectral_resolution = convert_ghz(
                    sp.spectralResolution.pyval,
                    sp.spectralResolution.attrib['unit']
                )
                representative_win = sp.representativeWindow.pyval
                isskyfreq = sp.isSkyFrequency.pyval
                group_index = sp.groupIndex.pyval
                self.sg_specwindows.append([
                    sg_id, spw_index, transition_name, centerfrequency,
                    bandwidth, spectral_resolution, representative_win,
                    isskyfreq, group_index
                ])

        # Correct AR and LAS to equivalent resolutions at 100GHz
        ar_cor = ar * repfreq / 100.
        las_cor = las * repfreq / 100.

        # set variables that will be filled later. The relevant variable to
        # calculate new minAR and maxAR is two_12m, False if needs one 12m conf.

        two_12m = None
        targets = sg.findall(prj + 'TargetParameters')
        num_targets = len(targets)
        c = 1
        for t in targets:
            self.read_pro_targets(t, sg_id, self.obsproject_uid, c)
            c += 1

        try:
            twelvetime = convert_tsec(
                sg.estimated12mTime.pyval,
                sg.estimated12mTime.attrib['unit']) / 3600.
            acatime = convert_tsec(
                sg.estimatedACATime.pyval,
                sg.estimatedACATime.attrib['unit']) / 3600.
            seventime = convert_tsec(
                float(sg.estimated7mTime.pyval),
                sg.estimated7mTime.attrib['unit']) / 3600.
            tptime = convert_tsec(
                sg.estimatedTPTime.pyval,
                sg.estimatedTPTime.attrib['unit']) / 3600.
        except AttributeError:
            twelvetime = None
            acatime = None
            seventime = None
            tptime = None

        # Stores Science Goal parameters in a data frame instance

        self.sciencegoals.append([
            sg_id, self.obsproject_uid, ous_id, sg_name, bands, estimatedtime,
            twelvetime, acatime, seventime, tptime, ar, las, ar_cor,
            las_cor, sensitivity, useaca, usetp, istimeconstrained, repfreq,
            repfreq_spec, singlecont_freq, calspecial,
            ispointsource, polarization, is_spec_scan, type_pol, hassb, two_12m,
            num_targets, sg_mode]
        )

    def read_pro_targets(self, target, sgid, obsp_uid, c):

        tid = sgid + '_' + str(c)
        try:
            solar_system = target.attrib['solarSystemObject']
        except KeyError:
            solar_system = None

        typetar = target.attrib['type']
        sourcename = target.sourceName.pyval
        coord = target.sourceCoordinates
        coord_type = coord.attrib['system']
        if coord_type in ['J2000', 'ICRS']:
            ra = convert_deg(coord.findall(val + 'longitude')[0].pyval,
                             coord.findall(val + 'longitude')[0].attrib['unit'])
            dec = convert_deg(coord.findall(val + 'latitude')[0].pyval,
                              coord.findall(val + 'latitude')[0].attrib['unit'])
        elif coord_type == 'galactic':
            lon = convert_deg(
                coord.findall(val + 'longitude')[0].pyval,
                coord.findall(val + 'longitude')[0].attrib['unit'])
            lat = convert_deg(
                coord.findall(val + 'latitude')[0].pyval,
                coord.findall(val + 'latitude')[0].attrib['unit'])
            eph = ephem.Galactic(pd.np.radians(lon), pd.np.radians(lat))
            ra = pd.np.degrees(eph.to_radec()[0])
            dec = pd.np.degrees(eph.to_radec()[1])
        else:
            print "coord type is %s, deal with it" % coord_type
            ra = convert_deg(coord.findall(val + 'longitude')[0].pyval,
                             coord.findall(val + 'longitude')[0].attrib['unit'])
            dec = convert_deg(coord.findall(val + 'latitude')[0].pyval,
                              coord.findall(val + 'latitude')[0].attrib['unit'])
        try:
            ismosaic = target.isMosaic.pyval
        except AttributeError:
            ismosaic = None

        sourcevelocity = target.sourceVelocity
        try:
            centervelocity = sourcevelocity.findall(
                val + 'centervelocity')[0].pyval
            centervelocity_units = sourcevelocity.findall(
                val + 'centervelocity')[0].attrib['unit']
            centervelocity_refsys = sourcevelocity.attrib['referenceSystem']
            centervelocity_dopp = sourcevelocity.attrib['dopplerCalcType']
        except:
            centervelocity = None
            centervelocity_units = None
            centervelocity_refsys = None
            centervelocity_dopp = None

        expectedprop = target.ExpectedProperties
        expected_linewidth = convert_ghz(
            expectedprop.expectedLineWidth.pyval,
            expectedprop.expectedLineWidth.attrib['unit']
        )

        self.sg_targets.append(
            [tid, obsp_uid, sgid, typetar, solar_system, sourcename, ra, dec,
             ismosaic, centervelocity, centervelocity_units,
             centervelocity_refsys, centervelocity_dopp, expected_linewidth])

# TODO: Implement get original estimated times from OT
    # def get_times(self):
    #     try:
    #         propf = self.data.ProposalFeedback
    #         arrays = propf
    #     except:
    #         time12 = 0
    #         timeaca = 0
    #         time7 = 0
    #         timetp = 0
    #         timebl = 0


class ObsProject(object):

    def __init__(self, xml_file, path='./'):
        """
        Notes
        -----

        ObsProject level:
        - isDDT may or may not be present, but we assume is unique.

        ScienceGoal level:
        - We only look for ScienceGoals. If a ScienceGoal has an ObsUnitSetRef
          then it might has SBs, but we assume there is only one OUSRef.
        - For the estimatedTotalTime, we assume it is the sum of the OT
          calculations, incluing ExtT, CompT, ACAT, TPT
        - Cycle 1 and 2 have only one band as requirement, supposely, but we
          check for more just in case.

        PerformanceParameters level:
        - Only one representativeFrequency assumed

        :param xml_file:
        :param path:
        """
        io_file = open(path + xml_file)
        # noinspection PyBroadException
        try:
            tree = objectify.parse(io_file)
        except:
            if xml_file == "uid___A001_X1ee_X1234.xml":
                io_file.close()
                io_file = open('/home/itoledo/Work/APA3/conf/' + xml_file)
                tree = objectify.parse(io_file)
        io_file.close()
        # noinspection PyUnboundLocalVariable
        self.data = tree.getroot()

        self.sg_targets = []
        self.sciencegoals = []
        self.visits = []
        self.temp_param = []
        self.sg_specwindows = []
        self.sg_specscan = []
        self.sg_sb = []

    def get_sg_sb(self):
        obsprog = self.data.ObsProgram
        op = obsprog.ObsPlan
        oussg_list = op.findall(prj + 'ObsUnitSet')
        for oussg in oussg_list:
            groupous_list = oussg.findall(prj + 'ObsUnitSet')
            ous_id = oussg.attrib['entityPartId']
            ous_name = oussg.name.pyval
            obsproject_uid = oussg.ObsProjectRef.attrib['entityId']

            # Now we iterate over all the children OUS (group ous and member
            # ous) until we find "SchedBlockRef" tags at the member ous
            # level.
            for groupous in groupous_list:
                gous_id = groupous.attrib['entityPartId']
                mous_list = groupous.findall(prj + 'ObsUnitSet')
                gous_name = groupous.name.pyval
                for mous in mous_list:
                    mous_id = mous.attrib['entityPartId']
                    mous_name = mous.name.pyval
                    try:
                        # noinspection PyUnusedLocal
                        sblist = mous.findall(prj + 'ObsUnitSet')
                        # noinspection PyUnusedLocal
                        sb_uid = mous.SchedBlockRef.attrib['entityId']
                    except AttributeError:
                        continue
                    oucontrol = mous.ObsUnitControl
                    execount = oucontrol.aggregatedExecutionCount.pyval
                    array = mous.ObsUnitControl.attrib['arrayRequested']
                    for sbs in mous.SchedBlockRef:
                        sb_uid = sbs.attrib['entityId']
                        self.sg_sb.append(
                            [sb_uid, obsproject_uid, ous_name, ous_id,
                             gous_id, gous_name, mous_id, mous_name, array,
                             execount])

    def get_info(self):

        code = self.data.code.pyval
        prj_version = self.data.version.pyval
        staff_note = self.data.staffProjectNote.pyval
        is_calibration = self.data.isCalibration.pyval
        obsproject_uid = self.data.ObsProjectEntity.attrib['entityId']
        obsproposal_uid = self.data.ObsProposalRef.attrib['entityId']
        try:
            obsreview_uid = self.data.ObsReviewRef.attrib['entityId']
        except AttributeError:
            obsreview_uid = None

        try:
            is_ddt = self.data.isDDT.pyval
        except AttributeError:
            is_ddt = False

        return [code, obsproject_uid, obsproposal_uid, obsreview_uid,
                prj_version, staff_note, is_calibration, is_ddt]

    # noinspection PyAttributeOutsideInit
    def get_sg(self):
        self.obsproject_uid = self.data.ObsProjectEntity.attrib['entityId']
        obsprog = self.data.ObsProgram
        sg_list = obsprog.findall(prj + 'ScienceGoal')
        c = 1
        for sg in sg_list:
            self.read_ph1_sg(sg, str("%02d" % c))
            c += 1

    def read_ph1_sg(self, sg, idnum):

        sg_id = self.obsproject_uid + '_' + str(idnum)

        # Handle exceptions of Science Goals without ObsUnitSets or SchedBlocks
        try:
            # ous_id = the id of associated ObsUnitSet at the ObsProgram level.
            ous_id = sg.ObsUnitSetRef.attrib['partId']
            hassb = True
        except AttributeError:
            ous_id = None
            hassb = False

        # get SG name, bands and estimated time
        sg_name = sg.name.pyval
        try:
            sg_mode = sg.attrib['mode']
        except KeyError:
            # print sg_id
            sg_mode = None
        bands = sg.findall(prj + 'requiredReceiverBands')[0].pyval
        estimatedtime = convert_tsec(
            sg.estimatedTotalTime.pyval,
            sg.estimatedTotalTime.attrib['unit']) / 3600.

        # get SG's AR (in arcsec), LAS (arcsec), sensitivity (Jy), useACA and
        # useTP
        performance = sg.PerformanceParameters
        ar = convert_sec(
            performance.desiredAngularResolution.pyval,
            performance.desiredAngularResolution.attrib['unit'])
        las = convert_sec(
            performance.desiredLargestScale.pyval,
            performance.desiredLargestScale.attrib['unit'])
        sensitivity = convert_jy(
            performance.desiredSensitivity.pyval,
            performance.desiredSensitivity.attrib['unit'])
        useaca = performance.useACA.pyval
        usetp = performance.useTP.pyval
        ispointsource = performance.isPointSource.pyval

        # Check if it is a TimeConstrained SG
        try:
            istimeconstrained = performance.isTimeConstrained.pyval
        except AttributeError:
            istimeconstrained = None

        if istimeconstrained:
            try:
                visit = performance.VisitConstraint
                for v in visit:
                    try:
                        starttime = v.startTime.pyval
                    except AttributeError:
                        starttime = None
                    try:
                        allowedmargin = v.allowedMargin.pyval
                        allowedmargin_unit = v.allowedMargin.attrib['unit']
                    except AttributeError:
                        allowedmargin = None
                        allowedmargin_unit = None
                    try:
                        note = v.note.pyval
                    except AttributeError:
                        note = None
                    isavoidconstraint = v.isAvoidConstraint.pyval
                    priority = v.priority.pyval
                    try:
                        isfixedstart = v.isFixedStart.pyval
                    except AttributeError:
                        isfixedstart = None

                    visitid = v.visitId.pyval
                    prev_visitid = v.previousVisitId.pyval
                    try:
                        requireddelay = v.requiredDelay.pyval
                        requireddelay_unit = v.requiredDelay.attrib['unit']
                    except AttributeError:
                        requireddelay = None
                        requireddelay_unit = None
                    self.visits.append([
                        sg_id, sg_name, self.obsproject_uid,
                        starttime, allowedmargin, allowedmargin_unit, note,
                        isavoidconstraint, priority, visitid, prev_visitid,
                        requireddelay, requireddelay_unit, isfixedstart])
            except AttributeError:
                try:
                    temp = performance.TemporalParameters
                except AttributeError:
                    temp = performance.MonitoringConstraint
                for t in temp:
                    starttime = t.startTime.pyval
                    try:
                        endtime = t.endTime.pyval
                    except AttributeError:
                        endtime = None
                    allowedmargin = t.allowedMargin.pyval
                    allowedmargin_unit = t.allowedMargin.attrib['unit']
                    try:
                        repeats = t.repeats.pyval
                    except AttributeError:
                        repeats = None
                    try:
                        lstmin = t.lSTMin.pyval
                        lstmax = t.lSTMax.pyval
                    except AttributeError:
                        lstmin = None
                        lstmax = None
                    try:
                        note = t.note.pyval
                    except AttributeError:
                        note = None
                    isavoidconstraint = t.isAvoidConstraint.pyval
                    priority = t.priority.pyval
                    fixedstart = t.isFixedStart.pyval
                    self.temp_param.append([
                        sg_id, sg_name, self.obsproject_uid,
                        starttime, endtime, allowedmargin, allowedmargin_unit,
                        repeats, lstmin, lstmax, note, isavoidconstraint,
                        priority, fixedstart
                    ])

        # Get SG representative Frequency, polarization configuration.
        calparam = sg.CalibrationSetupParameters
        calspecial = False
        if calparam.attrib['selection'] == 'user':
            calspecial = True

        spectral = sg.SpectralSetupParameters
        repfreq = convert_ghz(
            performance.representativeFrequency.pyval,
            performance.representativeFrequency.attrib['unit'])
        repfreq_spec = convert_ghz(
            spectral.representativeFrequency.pyval,
            spectral.representativeFrequency.attrib['unit'])

        polarization = spectral.attrib['polarisation']
        type_pol = spectral.attrib['type']
        specscan = spectral.findall(prj + 'SpectralScan')
        try:
            singlecontfreq = convert_ghz(
                spectral.singleContinuumFrequency.pyval,
                spectral.singleContinuumFrequency.attrib['unit']
            )
        except AttributeError:
            print "Single ContFrequency parse issue"
            singlecontfreq = None

        spw = spectral.findall(prj + 'ScienceSpectralWindow')
        is_spec_scan = False
        if len(specscan) > 0:
            is_spec_scan = True
            for n in range(len(specscan)):
                ss = specscan[n]
                ss_index = ss['index'].pyval
                startfrequency = convert_ghz(
                    ss.startFrequency.pyval,
                    ss.startFrequency.attrib['unit'])
                endfrequency = convert_ghz(
                    ss.endFrequency.pyval,
                    ss.endFrequency.attrib['unit'])
                bandwidth = convert_ghz(
                    ss.bandWidth.pyval,
                    ss.bandWidth.attrib['unit']
                )
                specres = convert_ghz(
                    ss.spectralResolution.pyval,
                    ss.spectralResolution.attrib['unit']
                )
                isskyfreq = ss.isSkyFrequency.pyval

                self.sg_specscan.append([
                    sg_id, ss_index, startfrequency, endfrequency,
                    bandwidth, specres, isskyfreq
                ])

        else:
            for n in range(len(spw)):
                sp = spw[n]
                spw_index = sp['index'].pyval
                transitionname = sp.transitionName.pyval
                centerfrequency = convert_ghz(
                    sp.centerFrequency.pyval,
                    sp.centerFrequency.attrib['unit']
                )
                bandwidth = convert_ghz(
                    sp.bandWidth.pyval,
                    sp.bandWidth.attrib['unit']
                )
                spectral_resolution = convert_ghz(
                    sp.spectralResolution.pyval,
                    sp.spectralResolution.attrib['unit']
                )
                representative_win = sp.representativeWindow.pyval
                isskyfreq = sp.isSkyFrequency.pyval
                groupindex = sp.groupIndex.pyval
                self.sg_specwindows.append([
                    sg_id, spw_index, transitionname, centerfrequency,
                    bandwidth, spectral_resolution, representative_win,
                    isskyfreq, groupindex
                ])

        # Correct AR and LAS to equivalent resolutions at 100GHz
        arcor = ar * repfreq / 100.
        lascor = las * repfreq / 100.

        # set variables that will be filled later. The relevant variable to
        # calculate new minAR and maxAR is two_12m, False if needs one 12m conf.

        two_12m = None
        targets = sg.findall(prj + 'TargetParameters')
        num_targets = len(targets)
        c = 1
        for t in targets:
            self.read_pro_targets(t, sg_id, self.obsproject_uid, c)
            c += 1

        try:
            twelvetime = convert_tsec(
                sg.estimated12mTime.pyval,
                sg.estimated12mTime.attrib['unit']) / 3600.
            acatime = convert_tsec(
                sg.estimatedACATime.pyval,
                sg.estimatedACATime.attrib['unit']) / 3600.
            seventime = convert_tsec(
                float(sg.estimated7mTime.pyval),
                sg.estimated7mTime.attrib['unit']) / 3600.
            tptime = convert_tsec(
                sg.estimatedTPTime.pyval,
                sg.estimatedTPTime.attrib['unit']) / 3600.
        except AttributeError:
            twelvetime = None
            acatime = None
            seventime = None
            tptime = None

        # Stores Science Goal parameters in a data frame instance

        self.sciencegoals.append([
            sg_id, self.obsproject_uid, ous_id, sg_name, bands, estimatedtime,
            twelvetime, acatime, seventime, tptime, ar, las, arcor,
            lascor, sensitivity, useaca, usetp, istimeconstrained, repfreq,
            repfreq_spec, singlecontfreq, calspecial,
            ispointsource, polarization, is_spec_scan, type_pol, hassb, two_12m,
            num_targets, sg_mode]
        )

    def read_pro_targets(self, target, sgid, obsp_uid, c):

        tid = sgid + '_' + str(c)
        try:
            solarsystem = target.attrib['solarSystemObject']
        except KeyError:
            solarsystem = None

        typetar = target.attrib['type']
        sourcename = target.sourceName.pyval
        coord = target.sourceCoordinates
        coord_type = coord.attrib['system']
        if coord_type in ['J2000', 'ICRS']:
            ra = convert_deg(coord.findall(val + 'longitude')[0].pyval,
                             coord.findall(val + 'longitude')[0].attrib['unit'])
            dec = convert_deg(coord.findall(val + 'latitude')[0].pyval,
                              coord.findall(val + 'latitude')[0].attrib['unit'])
        elif coord_type == 'galactic':
            lon = convert_deg(
                coord.findall(val + 'longitude')[0].pyval,
                coord.findall(val + 'longitude')[0].attrib['unit'])
            lat = convert_deg(
                coord.findall(val + 'latitude')[0].pyval,
                coord.findall(val + 'latitude')[0].attrib['unit'])
            eph = ephem.Galactic(pd.np.radians(lon), pd.np.radians(lat))
            ra = pd.np.degrees(eph.to_radec()[0])
            dec = pd.np.degrees(eph.to_radec()[1])
        else:
            print "coord type is %s, deal with it" % coord_type
            ra = convert_deg(coord.findall(val + 'longitude')[0].pyval,
                             coord.findall(val + 'longitude')[0].attrib['unit'])
            dec = convert_deg(coord.findall(val + 'latitude')[0].pyval,
                              coord.findall(val + 'latitude')[0].attrib['unit'])
        try:
            ismosaic = target.isMosaic.pyval
        except AttributeError:
            ismosaic = None

        sourcevelocity = target.sourceVelocity
        try:
            centervelocity = sourcevelocity.findall(
                val + 'centervelocity')[0].pyval
            centervelocity_units = sourcevelocity.findall(
                val + 'centervelocity')[0].attrib['unit']
            centervelocity_refsys = sourcevelocity.attrib['referenceSystem']
            centervelocity_dopp = sourcevelocity.attrib['dopplerCalcType']
        except AttributeError:
            centervelocity = None
            centervelocity_units = None
            centervelocity_refsys = None
            centervelocity_dopp = None

        expectedprop = target.ExpectedProperties
        expected_linewidth = convert_ghz(
            expectedprop.expectedLineWidth.pyval,
            expectedprop.expectedLineWidth.attrib['unit']
        )

        self.sg_targets.append(
            [tid, obsp_uid, sgid, typetar, solarsystem, sourcename, ra, dec,
             ismosaic, centervelocity, centervelocity_units,
             centervelocity_refsys, centervelocity_dopp, expected_linewidth])


# noinspection PyBroadException
class SchedBlock(object):

    def __init__(self, xml_file, sb_uid, obs_uid, ous_id, sg_id,
                 path='./'):
        """

        :param xml_file:
        :param path:
        """
        io_file = open(path + xml_file)
        tree = objectify.parse(io_file)
        io_file.close()
        self.data = tree.getroot()
        self.sb_uid = sb_uid
        self.ous_id = ous_id
        self.obs_uid = obs_uid
        self.sg_id = sg_id

    def read_schedblocks(self):

        # Open SB with SB parser class
        """

        """

        # Extract root level data
        array = self.data.findall(
            './/' + prj + 'ObsUnitControl')[0].attrib['arrayRequested']
        name = self.data.findall('.//' + prj + 'name')[0].pyval
        note = self.data.find('.//' + prj + 'note').pyval
        type12m = 'None'
        if name.rfind('TC') != -1:
            type12m = 'Comp'
        elif array == 'TWELVE-M':
            type12m = 'Ext'
        status = self.data.attrib['status']

        schedconstr = self.data.SchedulingConstraints
        schedcontrol = self.data.SchedBlockControl
        preconditions = self.data.Preconditions
        weather = preconditions.findall('.//' + prj + 'WeatherConstraints')[0]
        ouc = self.data.find('.//' + prj + 'ObsUnitControl')
        estimated_time_tag = ouc.find('.//' + prj + 'estimatedExecutionTime')
        estimatedtime = convert_thour(
            estimated_time_tag.pyval,
            estimated_time_tag.attrib['unit'])
        maximum_time_tag = ouc.find('.//' + prj + 'maximumtime')
        maximumtime = convert_thour(
            maximum_time_tag.pyval,
            maximum_time_tag.attrib['unit'])

        try:
            # noinspection PyUnusedLocal
            polarparam = self.data.PolarizationCalParameters
            ispolarization = True
        except AttributeError:
            ispolarization = False

        repfreq = schedconstr.representativeFrequency.pyval
        ra = schedconstr.representativeCoordinates.findall(
            val + 'longitude')[0].pyval
        dec = schedconstr.representativeCoordinates.findall(
            val + 'latitude')[0].pyval
        minar_old = schedconstr.minAcceptableAngResolution.pyval
        maxar_old = schedconstr.maxAcceptableAngResolution.pyval
        band = schedconstr.attrib['representativeReceiverBand']

        execount = schedcontrol.executionCount.pyval
        maxpwv = weather.maxPWVC.pyval

        n_fs = len(self.data.FieldSource)
        n_tg = len(self.data.Target)
        n_ss = len(self.data.SpectralSpec)
        try:
            n_sp = len(self.data.ScienceParameters)
        except AttributeError:
            n_sp = 0
            print "\nWarning, %s is malformed" % self.sb_uid
        try:
            n_acp = len(self.data.AmplitudeCalParameters)
        except AttributeError:
            n_acp = 0

        try:
            n_bcp = len(self.data.BandpassCalParameters)
        except AttributeError:
            n_bcp = 0

        try:
            n_pcp = len(self.data.PhaseCalParameters)
        except AttributeError:
            n_pcp = 0

        try:
            n_ogroup = len(self.data.ObservingGroup)
        except AttributeError:
            n_ogroup = 0

        rf = []
        new = True
        for n in range(n_fs):
            if new:
                rf.append(self.read_fieldsource(
                    self.data.FieldSource[n], self.sb_uid, array))
                new = False
            else:
                rf.append(self.read_fieldsource(
                    self.data.FieldSource[n], self.sb_uid, array))

        tar = []
        new = True
        for n in range(n_tg):
            if new:
                tar.append(
                    self.read_target(self.data.Target[n], self.sb_uid))
                new = False
            else:
                tar.append(self.read_target(self.data.Target[n], self.sb_uid))

        spc = []
        bb = []
        spw = []
        new = True
        for n in range(n_ss):
            if new:
                r = self.read_spectralconf(self.data.SpectralSpec[n],
                                           self.sb_uid)
                spc.append(r[0])
                bb.extend(r[1])
                spw.extend(r[2])
                new = False
            else:
                r = self.read_spectralconf(self.data.SpectralSpec[n],
                                           self.sb_uid)
                spc.append(r[0])
                bb.extend(r[1])
                spw.extend(r[2])

        scpar = []
        for n in range(n_sp):
            sp = self.data.ScienceParameters[n]
            en_id = sp.attrib['entityPartId']
            namep = sp.name.pyval
            rep_bw = convert_ghz(sp.representativeBandwidth.pyval,
                                 sp.representativeBandwidth.attrib['unit'])
            sen_goal = sp.sensitivityGoal.pyval
            sen_goal_u = sp.sensitivityGoal.attrib['unit']
            int_time = convert_tsec(sp.integrationTime.pyval,
                                    sp.integrationTime.attrib['unit'])
            subs_dur = convert_tsec(sp.subScanDuration.pyval,
                                    sp.subScanDuration.attrib['unit'])
            scpar.append([en_id, self.sb_uid, namep, rep_bw, sen_goal,
                          sen_goal_u, int_time, subs_dur])

        acpar = []
        if n_acp > 0:
            for n in range(n_acp):
                sp = self.data.AmplitudeCalParameters[n]
                en_id = sp.attrib['entityPartId']
                namep = sp.name.pyval
                int_time = convert_tsec(
                    sp.defaultIntegrationTime.pyval,
                    sp.defaultIntegrationTime.attrib['unit'])
                subs_dur = convert_tsec(sp.subScanDuration.pyval,
                                        sp.subScanDuration.attrib['unit'])
                acpar.append([en_id, self.sb_uid, namep, int_time, subs_dur])

        bcpar = []
        if n_bcp > 0:
            for n in range(n_bcp):
                sp = self.data.BandpassCalParameters[n]
                en_id = sp.attrib['entityPartId']
                namep = sp.name.pyval
                int_time = convert_tsec(
                    sp.defaultIntegrationTime.pyval,
                    sp.defaultIntegrationTime.attrib['unit'])
                subs_dur = convert_tsec(sp.subScanDuration.pyval,
                                        sp.subScanDuration.attrib['unit'])
                bcpar.append([en_id, self.sb_uid, namep, int_time, subs_dur])

        pcpar = []
        if n_pcp > 0:
            for n in range(n_pcp):
                sp = self.data.PhaseCalParameters[n]
                en_id = sp.attrib['entityPartId']
                namep = sp.name.pyval
                int_time = convert_tsec(
                    sp.defaultIntegrationTime.pyval,
                    sp.defaultIntegrationTime.attrib['unit'])
                subs_dur = convert_tsec(sp.subScanDuration.pyval,
                                        sp.subScanDuration.attrib['unit'])
                pcpar.append([en_id, self.sb_uid, namep, int_time, subs_dur])

        ordtar = []
        if n_ogroup > 0:
            for n in range(n_ogroup):
                ogroup = self.data.ObservingGroup[n]
                nameo = ogroup.name.pyval
                try:
                    n_otar = len(ogroup.OrderedTarget)
                except AttributeError:
                    continue
                if n_otar > 0:
                    for o in range(n_otar):
                        otar = ogroup.OrderedTarget[o]
                        index = 0
                        tar_ref = otar.TargetRef.attrib['partId']
                        ordtar.append([tar_ref, self.sb_uid, index, nameo])
                else:
                    continue

        return (self.sb_uid, self.obs_uid, self.sg_id, self.ous_id,
                name, note, status, float(repfreq), band, array,
                float(ra), float(dec), float(minar_old), float(maxar_old),
                int(execount), ispolarization, float(maxpwv),
                type12m, estimatedtime, maximumtime
                ), rf, tar, spc, bb, spw, scpar, acpar, bcpar, pcpar, ordtar

    @staticmethod
    def read_fieldsource(fs, sbuid, array):
        """

        :param fs:
        :param sbuid:
        """
        partid = fs.attrib['entityPartId']
        coord = fs.sourceCoordinates
        solarsystem = fs.attrib['solarSystemObject']
        sourcename = fs.sourceName.pyval
        name = fs.name.pyval
        isquery = fs.isQuery.pyval
        pointings = len(fs.findall(sbl + 'PointingPattern/' + sbl +
                                   'phaseCenterCoordinates'))
        try:
            ismosaic = fs.PointingPattern.isMosaic.pyval
        except AttributeError:
            ismosaic = False
        if isquery:
            querysource = fs.QuerySource
            qc_intendeduse = querysource.attrib['intendedUse']
            qcenter = querysource.queryCenter
            qc_ra = qcenter.findall(val + 'longitude')[0].pyval
            qc_dec = qcenter.findall(val + 'latitude')[0].pyval
            qc_use = querysource.use.pyval
            qc_radius = querysource.searchRadius.pyval
            qc_radius_unit = querysource.searchRadius.attrib['unit']
        else:
            qc_intendeduse, qc_ra, qc_dec, qc_use, qc_radius, qc_radius_unit = (
                None, None, None, None, None, None
            )
        coord_type = coord.attrib['system']
        if coord_type in ['J2000', 'ICRS']:
            ra = convert_deg(coord.findall(val + 'longitude')[0].pyval,
                             coord.findall(val + 'longitude')[0].attrib['unit'])
            dec = convert_deg(coord.findall(val + 'latitude')[0].pyval,
                              coord.findall(val + 'latitude')[0].attrib['unit'])
        elif coord_type == 'galactic':
            lon = convert_deg(
                coord.findall(val + 'longitude')[0].pyval,
                coord.findall(val + 'longitude')[0].attrib['unit'])
            lat = convert_deg(
                coord.findall(val + 'latitude')[0].pyval,
                coord.findall(val + 'latitude')[0].attrib['unit'])
            eph = ephem.Galactic(pd.np.radians(lon), pd.np.radians(lat))
            ra = pd.np.degrees(eph.to_radec()[0])
            dec = pd.np.degrees(eph.to_radec()[1])
        else:
            print "coord type is %s, deal with it" % coord_type
            ra = 0
            dec = 0
        if solarsystem == 'Ephemeris':
            ephemeris = fs.sourceEphemeris.pyval
        else:
            ephemeris = None

        return(
            partid, sbuid, solarsystem, sourcename, name, ra, dec, isquery,
            qc_intendeduse, qc_ra, qc_dec, qc_use, qc_radius, qc_radius_unit,
            ephemeris, pointings, ismosaic, array)

    @staticmethod
    def read_target(tg, sbuid):
        """

        :param tg:
        :param sbuid:
        """
        partid = tg.attrib['entityPartId']
        specref = tg.AbstractInstrumentSpecRef.attrib['partId']
        fieldref = tg.FieldSourceRef.attrib['partId']
        paramref = tg.ObservingParametersRef.attrib['partId']

        return (
            partid, sbuid, specref, fieldref, paramref)

    def read_spectralconf(self, ss, sbuid):
        """

        :param ss:
        :param sbuid:
        """

        name = ss.name.pyval
        partid = ss.attrib['entityPartId']
        freqconf = ss.FrequencySetup
        bb = self.read_baseband(partid, freqconf, sbuid)

        try:
            corrconf = ss.BLCorrelatorConfiguration
            spw = self.read_spectralwindow(corrconf, sbuid)
            nbb = len(corrconf.BLBaseBandConfig)
            nspw = 0
            for n in range(nbb):
                bbconf = corrconf.BLBaseBandConfig[n]
                nspw += len(bbconf.BLSpectralWindow)
        except AttributeError:
            corrconf = ss.ACACorrelatorConfiguration
            spw = self.read_spectralwindow(corrconf, sbuid)
            nbb = len(corrconf.ACABaseBandConfig)
            nspw = 0
            for n in range(nbb):
                bbconf = corrconf.ACABaseBandConfig[n]
                nspw += len(bbconf.ACASpectralWindow)

        spc = (partid, sbuid, name, nbb, nspw)

        return spc, bb, spw

    @staticmethod
    def read_baseband(spectconf, freqconf, sbuid):
        bbl = []

        # rest_freq = convert_ghz(freqconf.restFrequency.pyval,
        #                         freqconf.restFrequency.attrib['unit'])
        # trans_name = freqconf.transitionName.pyval
        # lo1_freq = convert_ghz(freqconf.lO1Frequency.pyval,
        #                        freqconf.lO1Frequency.attrib['unit'])
        # band = freqconf.attrib['receiverBand']
        # doppler_ref = freqconf.attrib['dopplerReference']

        for baseband in range(len(freqconf.BaseBandSpecification)):
            bb = freqconf.BaseBandSpecification[baseband]
            partid = bb.attrib['entityPartId']
            name = bb.attrib['baseBandName']
            center_freq_unit = bb.centerFrequency.attrib['unit']
            center_freq = convert_ghz(bb.centerFrequency.pyval,
                                      center_freq_unit)
            freq_switching = bb.frequencySwitching.pyval
            lo2_freq_unit = bb.lO2Frequency.attrib['unit']
            lo2_freq = convert_ghz(bb.lO2Frequency.pyval, lo2_freq_unit)
            weighting = bb.weighting.pyval
            use_usb = bb.useUSB.pyval
            bbl.append((partid, spectconf, sbuid, name, center_freq,
                        freq_switching, lo2_freq, weighting, use_usb))

        return bbl

    @staticmethod
    def read_spectralwindow(correconf, sbuid):
        spwl = []
        try:
            for baseband in range(len(correconf.BLBaseBandConfig)):
                bb = correconf.BLBaseBandConfig[baseband]
                bbref = bb.BaseBandSpecificationRef.attrib['partId']
                for sw in range(len(bb.BLSpectralWindow)):
                    spw = bb.BLSpectralWindow[sw]
                    # poln_prod = spw.attrib['polnProducts']
                    sideband = spw.attrib['sideband']
                    windows_function = spw.attrib['windowFunction']
                    name = spw.name.pyval
                    centerfreq_unit = spw.centerFrequency.attrib['unit']
                    centerfreq = convert_ghz(
                        spw.centerFrequency.pyval, centerfreq_unit)
                    averagingfactor = spw.spectralAveragingFactor.pyval
                    effectivebandwidth_unit = spw.effectiveBandwidth.attrib[
                        'unit']
                    effectivebandwidth = convert_ghz(
                        spw.effectiveBandwidth.pyval, effectivebandwidth_unit)
                    effective_channels = spw.effectiveNumberOfChannels.pyval
                    use = spw.useThisSpectralWindow.pyval
                    try:
                        spl = spw.SpectralLine
                        line_restfreq = convert_ghz(
                            spl.restFrequency.pyval,
                            spl.restFrequency.attrib['unit'])
                        line_name = spl.transition.pyval
                    except:
                        line_restfreq = 0
                        line_name = 'None'

                    spwl.append(
                        (bbref, sbuid, name, sideband, windows_function,
                         centerfreq, averagingfactor, effectivebandwidth,
                         effective_channels, line_restfreq, line_name, use))

        except AttributeError:
            for baseband in range(len(correconf.ACABaseBandConfig)):
                bb = correconf.ACABaseBandConfig[baseband]
                bbref = bb.BaseBandSpecificationRef.attrib['partId']
                for sw in range(len(bb.ACASpectralWindow)):
                    spw = bb.ACASpectralWindow[sw]
                    sideband = spw.attrib['sideband']
                    windows_function = spw.attrib['windowFunction']
                    name = spw.name.pyval
                    centerfreq_unit = spw.centerFrequency.attrib['unit']
                    centerfreq = convert_ghz(
                        spw.centerFrequency.pyval, centerfreq_unit)
                    averagingfactor = spw.spectralAveragingFactor.pyval
                    effectivebandwidth_unit = spw.effectiveBandwidth.attrib[
                        'unit']
                    effectivebandwidth = convert_ghz(
                        spw.effectiveBandwidth.pyval, effectivebandwidth_unit)
                    effective_channels = spw.effectiveNumberOfChannels.pyval
                    use = spw.useThisSpectralWindow.pyval
                    try:
                        spl = spw.SpectralLine
                        line_restfreq = convert_ghz(
                            spl.restFrequency.pyval,
                            spl.restFrequency.attrib['unit'])
                        line_name = spl.transition.pyval
                    except:
                        line_restfreq = 0
                        line_name = 'None'
                    spwl.append(
                        (bbref, sbuid, name, sideband, windows_function,
                         centerfreq, averagingfactor, effectivebandwidth,
                         effective_channels, line_restfreq, line_name, use))
        return spwl


class ObsReview(object):

    def __init__(self, xml_file, path='./'):
        """

        :param xml_file:
        :param path:
        """
        io_file = open(path + xml_file)
        tree = objectify.parse(io_file)
        io_file.close()
        self.data = tree.getroot()
        self.sg_sb = []

    def get_sg_sb(self):

        oplan = self.data.find('{Alma/ObsPrep/ObsProject}' + 'ObsPlan')
        oussg_list = oplan.findall(prj + 'ObsUnitSet')
        for oussg in oussg_list:
            groupous_list = oussg.findall(prj + 'ObsUnitSet')
            ous_id = oussg.attrib['entityPartId']
            ous_name = oussg.name.pyval
            obsproject_uid = oussg.ObsProjectRef.attrib['entityId']

            # Now we iterate over all the children OUS (group ous and member
            # ous) until we find "SchedBlockRef" tags at the member ous
            # level.
            for groupous in groupous_list:
                gous_id = groupous.attrib['entityPartId']
                mous_list = groupous.findall(prj + 'ObsUnitSet')
                gous_name = groupous.name.pyval
                for mous in mous_list:
                    mous_id = mous.attrib['entityPartId']
                    mous_name = mous.name.pyval
                    try:
                        # noinspection PyUnusedLocal
                        sblist = mous.findall(prj + 'ObsUnitSet')
                        # noinspection PyUnusedLocal
                        sb_uid = mous.SchedBlockRef.attrib['entityId']
                    except AttributeError:
                        continue
                    oucontrol = mous.ObsUnitControl
                    execount = oucontrol.aggregatedExecutionCount.pyval
                    array = mous.ObsUnitControl.attrib['arrayRequested']
                    for sbs in mous.SchedBlockRef:
                        sb_uid = sbs.attrib['entityId']
                        self.sg_sb.append(
                            [sb_uid, obsproject_uid, ous_name, ous_id,
                             gous_id, gous_name, mous_id, mous_name, array,
                             execount])
