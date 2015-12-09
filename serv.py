#!/usr/bin/env python
from twisted.web import xmlrpc, server


class DSACoreService(xmlrpc.XMLRPC):
    """
    A service to start as XML RPC interface to run the DSA Core
    """

    def __init__(self):
        xmlrpc.XMLRPC.__init__(self)
        import WtoDataBase3 as Data
        from astropy.utils.data import download_file
        from astropy.utils import iers
        iers.IERS.iers_table = iers.IERS_A.open(
            download_file(iers.IERS_A_URL, cache=True))
        self.data = Data.WtoDatabase3(refresh_apdm=True, allc2=False, loadp1=False)

    def xmlrpc_run(self,
                   array_kind='TWELVE-M',
                   prj_status=('Ready', 'InProgress'),
                   sb_status=('Ready', 'Suspend', 'Running', 'CalibratorCheck', 'Waiting'),
                   cycle=('2013.A', '2013.1', '2015.1', '2015.A'),
                   letter_grade=('A', 'B', 'C'),
                   bands=('ALMA_RB_03', 'ALMA_RB_04', 'ALMA_RB_06', 'ALMA_RB_07',
                          'ALMA_RB_08', 'ALMA_RB_09', 'ALMA_RB_10'),
                   check_count=True,
                   conf=None,
                   cal_blratio=False,
                   numant=None,
                   array_id=None,
                   horizon=20,
                   minha=-3.,
                   maxha=3.,
                   pwv=0.5):
        import WtoAlgorithm3 as Wto
        import WtoScorers3 as WtoScor

        dsa = Wto.WtoAlgorithm3(self.data)
        dsa.write_ephem_coords()
        dsa.static_param()

        dsa.set_time_now() #Parametrized

        dsa.selector(
            cycle=['2015.1', '2015.A'], minha=-4., maxha=4., letterg=['A', 'B'],
            array_id='last', pwv=0.5)

        scorer = dsa.master_wto_df.apply(
            lambda x: WtoScor.calc_all_scores(
                pwv, x['maxPWVC'], x['Exec. Frac'], x['sbName'], x['array'], x['ARcor'],
                x['DEC'], x['array_ar_cond'], x['minAR'], x['maxAR'], x['Observed'],
                x['EXECOUNT'], x['PRJ_SCIENTIFIC_RANK'], x['DC_LETTER_GRADE'],
                x['CYCLE'], x['HA']), axis=1)

        import pandas as pd
        fin = pd.merge(pd.merge(dsa.master_wto_df, dsa.selection_df, on='SB_UID'),
                       scorer.reset_index(), on='SB_UID').set_index(
            'SB_UID', drop=False)
        return fin.to_json(orient='index');

if __name__ == '__main__':
    from twisted.internet import reactor
    r = DSACoreService()
    reactor.listenTCP(7080, server.Site(r))
    reactor.run()

