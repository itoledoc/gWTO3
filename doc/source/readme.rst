************************
Requirements to run WTO3
************************


Anaconda environment
====================

name: root
dependencies:

- anaconda=2.4.0=np110py27_0
- anaconda-client=1.1.2=py27_0
- astropy=1.0.6=np110py27_0
- conda=3.18.6=py27_0
- conda-build=1.18.2=py27_0
- conda-env=2.4.4=py27_0
- cx_oracle=5.1.2=py27_0
- ephem=3.7.6.0=py27_0
- numpy=1.10.1=py27_0
- oracle-instantclient=11.2.0.4.0=0
- pandas=0.17.1=np110py27_0
- python=2.7.10=1
- python-dateutil=2.4.2=py27_0
- sqlalchemy=1.0.9=py27_0

Environment variables to be loaded
==================================

::

    export TNS_ADMIN=/path/to/tnsnames.ora
    export PATH="$HOME/anaconda/bin:$PATH"  --> path to the anaconda environment, in this case installed in the home directory
    export WTO="/path/to/gWTO3/"
    export CON_STR="almasu/alma4dba@ALMA_ONLINE.SCO.CL" --> conection string to archive. If in the OSF, "almasu/alma4dba@ALMA_ONLINE.OSF.CL"
    export APDM_C3="/path/to/save/apdms"
    export PYTHONPATH="$PYTHONPATH:/path/to/gWTO3"


Initialization of the Wto class
===============================

::

    import WtoAlgorithm3 as Wto
    import WtoScorers3 as WtoScor

    from astropy.utils.data import download_file
    from astropy.utils import iers
    iers.IERS.iers_table = iers.IERS_A.open(
        download_file(iers.IERS_A_URL, cache=True))

    datas = Wto.WtoAlgorithm3()


    datas.write_ephem_coords()
    datas.static_param()

    datas.selector(
        cycle=['2015.1', '2015.A'], minha=-4., maxha=4., letterg=['A', 'B'],
        array_id='last', pwv=0.5)

    scorer = datas.master_wto_df.apply(
        lambda x: WtoScor.calc_all_scores(
            1.3, x['maxPWVC'], x['Exec. Frac'], x['sbName'], x['array'], x['ARcor'],
            x['DEC'], x['array_ar_cond'], x['minAR'], x['maxAR'], x['Observed'],
            x['EXECOUNT'], x['PRJ_SCIENTIFIC_RANK'], x['DC_LETTER_GRADE'],
            x['CYCLE'], x['HA']), axis=1)

