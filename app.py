import streamlit as st, re, os, html, datetime as dt

st.set_page_config(page_title="MVS SYSPROG SIMULATOR", layout="wide")
HERE = os.path.dirname(os.path.abspath(__file__))
CSS = """<style>
.stApp,[data-testid=stSidebar]{background:#000;color:#33ff33}
*{font-family:'Courier New',monospace!important}
h1,h2,h3,p,label,span,li{color:#33ff33!important}
.wrap{display:flex;flex-direction:column-reverse;height:480px;overflow-y:auto;background:#000;
 border:2px solid #1a8f1a;box-shadow:0 0 18px #0a5a0a inset;padding:10px}
.crt{color:#33ff33;white-space:pre-wrap;font-size:14px;line-height:1.25;text-shadow:0 0 4px #0f0}
.hi{color:#fff}
input,textarea{background:#000!important;color:#33ff33!important;border:1px solid #1a8f1a!important}
.stButton button,.stFormSubmitButton button{background:#000;color:#33ff33;border:1px solid #33ff33}
.stButton button:hover,.stFormSubmitButton button:hover{background:#33ff33;color:#000}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

def now():
    n = dt.datetime.now()
    return n.strftime("%H.%M.%S"), n.strftime("%Y.%j"), n.strftime("%y%j")

DEV = {"0A80": ["3390", "SYSRES", "ONLINE"], "0A81": ["3390", "PAGE01", "ONLINE"],
       "0A82": ["3390", "SPOOL1", "ONLINE"], "0A83": ["3390", "WORK01", "ONLINE"],
       "0A84": ["3390", "USER01", "OFFLINE"], "0580": ["3480", "", "OFFLINE"],
       "0581": ["3480", "", "OFFLINE"], "0700": ["3270", "", "ONLINE"], "000C": ["2540R", "", "ONLINE"]}
CAT = {"SYS1.PARMLIB": "0A80", "SYS1.PROCLIB": "0A80", "SYS1.LINKLIB": "0A80", "SYS1.MACLIB": "0A80",
       "SYS1.MODGEN": "0A80", "SYS1.LPALIB": "0A80", "SYS1.VTAMLST": "0A80", "IBMUSER.JCL": "0A83",
       "IBMUSER.LOAD": "0A83", "IBMUSER.AWSTAPE.DATASET": "0A83", "SMPE.GLOBAL.CSI": "0A83"}
APF = ["SYS1.LINKLIB", "SYS1.SVCLIB", "SYS1.LPALIB", "IBMUSER.LOAD"]
TOOLS = {  # member: (file, title, [sim job output])
 "AWSSL": ("awssl-v19g", "AWSSL 1.9G - dataset <-> AWS virtual tape (standard labels)",
  ["AWSSL 1.9G AWS VIRTUAL TAPE", "AWSVOL  VOLSER=MYTAPE", "AWSPUT  INDSN=SYS1.PARMLIB  -> FILENO 1  SL=YES",
   "AWSPUT  INDSN=IBMUSER.JCL,UNLOAD=IEBCOPY -> FILENO 2", "AWS0010I 2 FILES, 1,204 BLOCKS WRITTEN TO AWSFILE", "AWS0099I NORMAL END, RC=0"]),
 "AWSWRITE": ("awswrite.jcl", "AWSWRITE - AWSTAPE disk image -> physical tape (BLP, UNIT=3480)",
  ["ASMA90 ASSEMBLY, 0 ERRORS", "IEWL LINK EDIT RC=0", "AWSWRITE: TAPEOUT OPENED UNIT 0580 BLP",
   "AWSWRITE: 3 FILES, 6 TAPE MARKS COPIED", "NOTE: JOBCLASS needs BLP=YES  ($TJOBCLASS(A),BLP=YES)"]),
 "RAWSTAPE": ("rawstape.jcl", "RAWSTAPE - extract file n from AWSTAPE as RECFM=U (PARM=filenumber)",
  ["ASMA90 RC=0  IEWL RC=0", "RAWSTAPE: PARM=3  SKIPPING FILES 1-2", "RAWSTAPE: 410 BLOCKS READ, 410 WRITTEN TO SYSUT2",
   "IEBGENER (SYSIN DUMMY) RC=0 - reblocks IBMUSER.SADUMP"]),
 "TAPECONV": ("tapeconv.jcl", "TAPECONV - tape file -> AWSTAPE format (LBI, blocks up to 65520)",
  ["ASMA90 RC=0  IEWL RC=0", "TAPECONV: SYSUT1 TAPE.DATASET VOL=AAAAAA OPENED",
   "TAPECONV: 5,120 BLOCKS CONVERTED, 6-BYTE AWS HEADERS ADDED", "SYSUT2 IBMUSER.AWSTAPE.DATASET CATALOGED"]),
 "CCKDDUMP": ("cckddump.hla", "CCKDDUMP - build compressed dasd (CCKD) file from SYSUT1 -> SYSUT2",
  ["CCKDDUMP 0.1.14  VOLSER=SYSRES", "CCKD0001I READING CKD 3390 UNIT, 3339 CYLS", "CCKD0010I 50,085 TRACKS, COMPRESSED 71%", "CCKD0099I RC=0"]),
 "CCKDLOAD": ("cckdload.hla", "CCKDLOAD - restore CCKD file to a real DASD unit (unit OFFLINE, APF STEPLIB)",
  ["CCKDLOAD PARM=0A84  UNIT MUST BE OFFLINE - CHECKED OK", "CCKD0002I CDEVHDR OPTIONS: LITTLE-ENDIAN", "CCKD0020I 3339 CYLS WRITTEN", "CCKD0099I RC=0"]),
 "DASDLIST": ("dasdlist.bat", "dasdlist.bat - Hercules utility wrapper: bash dasdlist %1..%5",
  ["dasdlist tk5res.cckd", "VOLSER SYSRES  CYLS 3339  DSCBs: 412", "SYS1.LINKLIB   PO FB 80  EXT 1", "SYS1.PARMLIB   PO FB 80  EXT 1"]),
}
EX = [  # (module, title, task, regex, hint, link)
 ("Operator", "Display system time", "Show the current time and date.", r"^(D|DISPLAY) T$", "D T", "z/OS MVS System Commands: DISPLAY T"),
 ("Operator", "Display IPL info", "Show IPL date, release and IPL volume.", r"^D IPLINFO$", "D IPLINFO", "System Commands: DISPLAY IPLINFO"),
 ("Operator", "Display processors", "Show CPU status.", r"^D M=CPU$", "D M=CPU", "System Commands: DISPLAY M"),
 ("Operator", "Active address spaces", "List active jobs and started tasks.", r"^D A,L$", "D A,L", "System Commands: DISPLAY A"),
 ("Operator", "Display DASD units", "Show 4 units starting at 0A80.", r"^D U,,,0A80,\d+$", "D U,,,0A80,4", "System Commands: DISPLAY U"),
 ("Operator", "Vary DASD online", "Bring 0A84 online.", r"^V 0A84,ONLINE$", "V 0A84,ONLINE", "System Commands: VARY"),
 ("Operator", "Vary DASD offline", "Take 0A84 offline (needed before CCKDLOAD).", r"^V 0A84,OFFLINE$", "V 0A84,OFFLINE", "System Commands: VARY"),
 ("Operator", "Mount a tape", "Mount SL volume AWS001 on 0580.", r"^M 0580,VOL=\(SL,AWS001\)$", "M 0580,VOL=(SL,AWS001)", "System Commands: MOUNT"),
 ("Operator", "Answer a WTOR", "Display outstanding replies, then answer.", r"^R 0?1,\w+", "D R,L then R 01,NOREQ", "System Commands: REPLY"),
 ("Operator", "Start / Modify / Stop a task", "Start TESTSTC (S), then stop it (P).", r"^P TESTSTC$", "S TESTSTC ... P TESTSTC", "System Commands: START/STOP"),
 ("Sysprog", "Display APF list", "Show authorized libraries.", r"^D PROG,APF$", "D PROG,APF", "System Commands: DISPLAY PROG"),
 ("Sysprog", "Display LNKLST", "Show the link list.", r"^D PROG,LNKLST$", "D PROG,LNKLST", "System Commands: DISPLAY PROG"),
 ("Sysprog", "Display PARMLIB concat", "Show PARMLIB datasets.", r"^D PARMLIB$", "D PARMLIB", "z/OS MVS Initialization and Tuning Reference"),
 ("Sysprog", "Page datasets", "Show auxiliary storage / page data sets.", r"^D ASM$", "D ASM", "System Commands: DISPLAY ASM"),
 ("JES2", "Display job class A", "Check JOBCLASS(A).", r"^\$DJOBCLASS\(A\)$", "$DJOBCLASS(A)", "JES2 Commands: $D JOBCLASS"),
 ("JES2", "Allow BLP for tape jobs", "Enable BLP in class A (AWSWRITE needs it).", r"^\$TJOBCLASS\(A\),BLP=YES$", "$TJOBCLASS(A),BLP=YES", "JES2 Commands: $T JOBCLASS"),
 ("JES2", "Display spool", "Show spool volumes.", r"^\$DSPOOL$", "$DSPOOL", "JES2 Commands: $D SPOOL"),
 ("JES2", "Display initiators", "Show initiators.", r"^\$DI$", "$DI", "JES2 Commands: $D I"),
 ("JES2", "Display job queue", "Show queued jobs.", r"^\$DQ$", "$DQ", "JES2 Commands: $D Q"),
 ("TSO", "List catalog", "List catalog entries for IBMUSER.", r"^LISTC LEVEL\(IBMUSER\)$", "LISTC LEVEL(IBMUSER)", "z/OS TSO/E Command Reference: LISTCAT"),
 ("TSO", "Submit a job", "Submit the AWSSL JCL.", r"^SUB(MIT)? .*AWSSL", "SUBMIT 'IBMUSER.JCL(AWSSL)'", "TSO/E: SUBMIT"),
 ("SDSF", "Job status", "Open SDSF status.", r"^ST$", "ST", "z/OS SDSF User's Guide"),
 ("SDSF", "Syslog", "Read the system log.", r"^LOG$", "LOG", "z/OS SDSF User's Guide"),
 ("Tape lab", "Run AWSSL", "Open Hercules Tools lab and run AWSSL.", r"^RUN:AWSSL$", "Use Tools Lab", "AWSSL header comments (Reed Petty)"),
 ("Tape lab", "Run RAWSTAPE", "Extract file 3 from an AWSTAPE.", r"^RUN:RAWSTAPE$", "Use Tools Lab", "rawstape.jcl"),
 ("Tape lab", "Run TAPECONV", "Convert a tape to AWSTAPE.", r"^RUN:TAPECONV$", "Use Tools Lab", "tapeconv.jcl"),
 ("Tape lab", "Run AWSWRITE", "Write an AWSTAPE to physical tape.", r"^RUN:AWSWRITE$", "Use Tools Lab", "awswrite.jcl"),
 ("DASD lab", "Run CCKDDUMP then CCKDLOAD", "Back up and restore a CCKD volume.", r"^RUN:CCKDLOAD$", "Use Tools Lab", "cckddump.hla / cckdload.hla"),
 ("SMP/E", "Set GLOBAL zone", "Point SMP/E at the global zone.", r"^SET BDY\(GLOBAL\)$", "SET BDY(GLOBAL)", "SMP/E Commands: SET"),
 ("SMP/E", "RECEIVE the dummy USERMOD", "Receive SYSMOD USR0001 (IEFBR14 dummy).", r"^RECEIVE S\(USR0001\)$", "RECEIVE S(USR0001)", "SMP/E Commands: RECEIVE"),
 ("SMP/E", "APPLY CHECK", "SET BDY(MVST100) then APPLY S(USR0001) CHECK.", r"^APPLY S\(USR0001\) CHECK$", "SET BDY(MVST100)", "SMP/E Commands: APPLY"),
 ("SMP/E", "APPLY", "Apply USR0001 to the target zone.", r"^APPLY S\(USR0001\)$", "APPLY S(USR0001)", "SMP/E Commands: APPLY"),
 ("SMP/E", "RESTORE", "Back it out (only before ACCEPT).", r"^RESTORE S\(USR0001\)$", "RESTORE S(USR0001)", "SMP/E Commands: RESTORE"),
 ("SMP/E", "ACCEPT", "APPLY again, SET BDY(MVSTD), then ACCEPT.", r"^ACCEPT S\(USR0001\)$", "ACCEPT S(USR0001)", "SMP/E Commands: ACCEPT"),
 ("SMP/E", "LIST SYSMOD", "Show SYSMOD status.", r"^LIST SYSMOD", "LIST SYSMOD(USR0001)", "SMP/E Commands: LIST"),
 ("IPL/PARMLIB", "List IEASYS00", "Display the system parameter member.", r"^LIST IEASYS00$", "LIST IEASYS00", "Initialization and Tuning Reference: IEASYSxx"),
 ("IPL/PARMLIB", "Change MAXUSER", "Set MAXUSER to 300.", r"^SET IEASYS00,MAXUSER=300$", "SET IEASYS00,MAXUSER=300", "IEASYSxx: MAXUSER"),
 ("IPL/PARMLIB", "Re-IPL with CLPA", "IPL 0A80 with CLPA so the change takes effect.", r"^IPL 0A80.*CLPA", "IPL 0A80,CLPA", "IPL and Program Management"),
 ("IPL/PARMLIB", "Dynamic APF add", "Add IBMUSER.UTILS to APF without IPL.", r"^SETPROG APF,ADD,DSNAME=\S+,VOLUME=\w+$", "SETPROG APF,ADD,DSNAME=IBMUSER.UTILS,VOLUME=WORK01", "System Commands: SETPROG"),
 ("JES2", "Hold a job", "SUBMIT a job in TSO, then hold it: $HJ(n).", r"^\$HJ\(\d+\)$", "$HJ(4)", "JES2 Commands: $H J"),
 ("JES2", "Cancel a job", "Cancel a job.", r"^\$CJ\(\d+\)$", "$CJ(4)", "JES2 Commands: $C J"),
 ("JES2", "Purge output", "Purge a job that has printed.", r"^\$PJ\(\d+\)$", "$PJ(3)", "JES2 Commands: $P J"),
 ("SDSF", "Output queue", "Show the output queue.", r"^O$", "O", "SDSF User's Guide"),
 ("SDSF", "Initiators", "Show initiators.", r"^I$", "I", "SDSF User's Guide"),
 ("SDSF", "View a job log", "Select a job: S JOB00003.", r"^S JOB\d+$", "S JOB00003", "SDSF User's Guide"),
 ("Lifecycle", "Watch INPUT > EXEC > OUTPUT", "In TSO: SUBMIT 'IBMUSER.JCL(AWSSL)'. Then press ENTER on ST in SDSF until the job shows PRINT.", r"^LIFECYCLE$", "Each command you type advances jobs one step", "JES2 job processing phases"),
 ("MVS Ref", "Display consoles", "Show active consoles (IBM System Commands: DISPLAY C).", r"^D C$", "D C", "MVS System Commands: DISPLAY C"),
 ("MVS Ref", "Resource contention", "Display GRS contention.", r"^D GRS,C$", "D GRS,C", "MVS System Commands: DISPLAY GRS"),
 ("MVS Ref", "Central storage", "Display real storage.", r"^D M=STOR$", "D M=STOR", "MVS System Commands: DISPLAY M"),
 ("MVS Ref", "Active batch jobs / TSO users", "List active jobs.", r"^D J,L$", "D J,L (then D TS,L)", "MVS System Commands: DISPLAY J / TS"),
 ("MVS Ref", "SMF data sets", "Show SMF recording data sets.", r"^D SMF$", "D SMF  (D SMF,O for options)", "MVS System Commands: DISPLAY SMF"),
 ("MVS Ref", "Static symbols", "Show system symbols.", r"^D SYMBOLS$", "D SYMBOLS", "MVS System Commands: DISPLAY SYMBOLS"),
 ("MVS Ref", "Command via JES2", "Issue an MVS command through JES2: $VS,'D T'.", r"^\$VS,", "$VS,'D T'", "MVS System Commands intro: $VS"),
 ("SMP/E", "ACCEPT CHECK", "SET BDY(MVSTD) and run ACCEPT CHECK before ACCEPT.", r"^ACCEPT S\(USR0001\) CHECK$", "ACCEPT S(USR0001) CHECK", "SMP/E Commands: ACCEPT CHECK facility"),
 ("SMP/E", "REPORT", "Run an SMP/E REPORT.", r"^REPORT ", "REPORT SYSMODS", "SMP/E User's Guide: Using the REPORT commands"),
 ("Zowe", "Point zwe at zowe.yaml", "Set the config variable so you can omit -c.", r"^EXPORT ZWE_CLI_PARAMETER_CONFIG=\S+$", "export ZWE_CLI_PARAMETER_CONFIG=/var/lpp/zowe/zowe.yaml", "Zowe docs: Installing from a convenience build"),
 ("Zowe", "zwe install", "Install the Zowe MVS data sets.", r"^ZWE INSTALL", "zwe install -c ./zowe.yaml", "Zowe docs: zwe install"),
 ("Zowe", "zwe init", "Run all init steps (mvs, vsam, apfauth, security, certificate, stc).", r"^ZWE INIT( -C \S+| --CONFIG \S+)?$", "zwe init   (or one by one: zwe init mvs ...)", "Zowe docs: Initializing the z/OS runtime"),
 ("Zowe", "zwe start", "Start Zowe (ZWESLSTC) then check D A,L on the console.", r"^ZWE START", "zwe start", "Zowe docs: Starting Zowe"),
 ("Zowe", "Zowe CLI: zosmf status", "Check z/OSMF connectivity.", r"^ZOWE ZOSMF CHECK STATUS$", "zowe zosmf check status", "Zowe CLI docs"),
 ("Zowe", "Zowe CLI: list jobs", "List jobs from your PC via z/OSMF.", r"^ZOWE JOBS LIST JOBS$", "zowe jobs list jobs", "Zowe CLI docs"),
 ("Zowe", "Zowe CLI: list data sets", "List IBMUSER data sets.", r"^ZOWE FILES LIST DS", "zowe files list ds \"ibmuser.*\"", "Zowe CLI docs"),
 ("Zowe", "zwe stop", "Stop Zowe.", r"^ZWE STOP", "zwe stop", "Zowe docs: Stopping Zowe"),
 ("Lifecycle", "Hold then release", "Submit, $HJ(n) at once, check ST shows HELD, then $AJ(n).", r"^\$AJ\(\d+\)$", "$AJ(n)", "JES2 Commands: $A J"),
]
S = st.session_state
if "init" not in S:
    S.init = True; S.dev = {k: v[:] for k, v in DEV.items()}; S.done = set(); S.cmds = []
    S.jobs = [["JES2", "STC00001", "STC", "ACTIVE"], ["MSTR", "STC00002", "STC", "ACTIVE"], ["IBMUSERA", "JOB00003", "A", "OUTPUT"]]
    S.wtor = {"01": "$HASP426 SPECIFY OPTIONS - JES2 SP 4.1.0 (reply NOREQ)"}; S.jn = 4; S.blp = "NO"
    S.log = {"con": [], "tso": ["READY"], "sdsf": ["SDSF  (type ST, DA, LOG, H)"]}
    S.syslog = ["IEF196I IEF285I   SYS1.PROCLIB  KEPT", "$HASP250 JES2 IS PURGED"]
    S.con_log = None
S.setdefault("smp", {"USR0001": "NONE"}); S.setdefault("zone", "GLOBAL"); S.setdefault("ok", True); S.setdefault("lc", False)
S.setdefault("parm", {"IEASYS00": {"SYSNAME": "MVSH", "MAXUSER": "255", "APF": "00", "LNK": "00", "SMF": "00", "CLPA": "NO", "PAGE": "(PAGE.PLPA,PAGE.COMMON,PAGE.LOCAL)"}, "SMFPRM00": {"ACTIVE": "", "DSNAME": "SYS1.MAN1", "SYS": "(NOTYPE(14,15))"}, "COMMND00": {"COM": "S JES2"}}); S.setdefault("chg", False); S.setdefault("zw", {"env": "", "inst": False, "init": set()})

def sysmsg(m): S.syslog.append(f"{now()[0]} {m}")

def tick():
    for j in S.jobs:
        if j[2] == "STC": continue
        if j[3] == "INPUT": j[3] = "ACTIVE"; sysmsg(f"$HASP373 {j[0]:8s} STARTED - INIT 1 - CLASS {j[2]} - SYS MVSH")
        elif j[3] == "ACTIVE":
            j[3] = "OUTPUT"; sysmsg(f"$HASP395 {j[0]:8s} ENDED"); sysmsg(f"$HASP150 {j[0]:8s} ON PRINTER1"); S.lc = True

def con(c):
    t, d, _ = now(); m = re.match
    if re.match(r"^(D|DISPLAY) T$", c):
        return [f"IEE136I LOCAL: TIME={t} DATE={d}  UTC: TIME={t} DATE={d}"]
    if c == "D IPLINFO":
        return [f"IEE254I {t} IPLINFO DISPLAY", " SYSTEM IPLED AT 08.00.00 ON 10/19/2026", " RELEASE MVS 3.8J (TK5)   IPL DEVICE 0A80 VOLUME SYSRES",
                " IEASYS LIST = (00)   IEASYM LIST = (00)  LOADxx = N/A (MVS 3.8: SYS1.PARMLIB(IEASYS00))"]
    if c == "D M=CPU":
        return [f"IEE174I {t} DISPLAY M", " PROCESSOR STATUS", " ID  CPU  SERIAL", " 00  +    0123452094", " CPC ND = 002094.S07.IBM.02.00000012345", " + ONLINE  - OFFLINE  . DOES NOT EXIST"]
    if c in ("D A,L", "D A,ALL"):
        r = [f"IEE114I {t} {d} ACTIVITY", " JOBS    M/S    TS USERS    SYSAS    INITS   ACTIVE/MAX VTAM    OAS",
             f" {len(S.jobs):05d}   00002   00001     00007    00010   00001/00010        00003", "  JOBNAME  STEPNAME PROCSTEP  JOBID"]
        return r + [f"  {j[0]:8s} {'STARTING' if j[2]=='STC' else '':8s} {'':8s} {j[1]}" for j in S.jobs if j[3] == "ACTIVE"]
    mm = re.match(r"^D U,(\w*),(\w*),([0-9A-F]{3,4}),?(\d+)?$", c)
    if mm:
        a0, n = mm.group(3).zfill(4), int(mm.group(4) or 1)
        r = [f"IEE457I {t} UNIT STATUS", "UNIT TYPE STATUS        VOLSER   VOLSTATE"]
        for a, v in sorted(S.dev.items())[:]:
            if a >= a0 and n > 0:
                r.append(f"{a} {v[0]:5s} {'O' if v[2]=='ONLINE' else 'F-NRD' if v[2]=='OFFLINE' else v[2]:11s} {v[1]:8s} {'PRIV/RSDNT' if v[1] else ''}"); n -= 1
        return r
    mm = re.match(r"^V ([0-9A-F]{3,4}),(ONLINE|OFFLINE)$", c)
    if mm:
        a = mm.group(1).zfill(4)
        if a not in S.dev: return [f"IEE313I {a} UNIT REF INVALID"]
        S.dev[a][2] = mm.group(2); sysmsg(f"IEE302I {a}     {mm.group(2)}")
        return [f"IEE302I {a}     {mm.group(2)}"]
    mm = re.match(r"^M ([0-9A-F]{3,4}),VOL=\(SL,(\w+)\)$", c)
    if mm:
        a = mm.group(1).zfill(4)
        if a not in S.dev or S.dev[a][0] != "3480": return ["IEE313I UNIT NOT A TAPE DEVICE"]
        S.dev[a][1:] = [mm.group(2), "ONLINE"]; return [f"IEC501A M {a},{mm.group(2)},SL", f"IEC705I TAPE ON {a},{mm.group(2)},SL"]
    if c == "D R,L":
        return [f"IEE112I {t} PENDING REQUESTS"] + ([" RM=1  IM=0  CEM=0  EM=0  RU=0  IR=0  AMRF=0"] + [f"*{k} {v}" for k, v in S.wtor.items()] if S.wtor else [" NO REQUESTS"])
    mm = re.match(r"^R (\d+),(.*)$", c)
    if mm:
        k = mm.group(1).zfill(2)
        if k in S.wtor: del S.wtor[k]; return [f"IEE600I REPLY TO {k} IS;{mm.group(2)}"]
        return [f"IEE708I {k} REPLY ID NOT OUTSTANDING"]
    if c == "D PROG,APF":
        return [f"CSV450I {t} DISPLAY PROG,APF", " FORMAT=DYNAMIC", " ENTRY VOLUME DSNAME"] + [f" {i+1:3d} SYSRES {x}" for i, x in enumerate(APF)]
    if c == "D PROG,LNKLST":
        return [f"CSV470I {t} LNKLST DISPLAY", " LNKLST SET LNKLST00", " ENTRY APF VOLUME DSNAME", " 1 YES SYSRES SYS1.LINKLIB", " 2 NO  SYSRES SYS1.MIGLIB"]
    if c == "D PARMLIB":
        return [f"IEE251I {t} PARMLIB DISPLAY", " ENTRY FLAGS VOLUME DATASET", " 1 S SYSRES SYS1.PARMLIB", " 2 S SYSRES SYS1.PARMLIB.USER"]
    if c == "D ASM":
        return [f"IEE200I {t} DISPLAY ASM", " TYPE FULL STAT DEV DATASET NAME", " PLPA 41% OK 0A81 PAGE.PLPA", " COMMON 12% OK 0A81 PAGE.COMMON", " LOCAL 07% OK 0A81 PAGE.LOCAL"]
    mm = re.match(r"^S (\w+)", c)
    if mm:
        n = mm.group(1); S.jobs.append([n, f"STC{S.jn:05d}", "STC", "ACTIVE"]); S.jn += 1; sysmsg(f"IEF403I {n} - STARTED")
        return [f"IEF403I {n} - STARTED - TIME={t}"]
    mm = re.match(r"^([PC]) (\w+)$", c)
    if mm:
        for j in S.jobs:
            if j[0] == mm.group(2) and j[3] == "ACTIVE":
                j[3] = "OUTPUT"; sysmsg(f"IEF404I {j[0]} - ENDED"); return [f"IEF404I {j[0]} - ENDED - TIME={t}"]
        return [f"IEE341I {mm.group(2)} NOT ACTIVE"]
    mm = re.match(r"^F (\w+),(.*)$", c)
    if mm: return [f"IEE122I MODIFY {mm.group(1)} ACCEPTED: {mm.group(2)}"]
    mm = re.match(r"^\$([HACPD])J\((?:JOB)?0*(\d+)\)$", c)
    if mm:
        op, n = mm.groups(); j = next((x for x in S.jobs if x[2] != "STC" and int(x[1][3:]) == int(n)), None)
        if not j: return [f"$HASP003 RC=(03),$%sJ - JOB {n} NOT FOUND" % op]
        if op == "D": return [f"$HASP890 JOB({j[1]}) JOBNAME={j[0]},STATUS=({j[3]}),CLASS={j[2]}"]
        if op == "H" and j[3] == "INPUT": j[3] = "HELD"; return [f"$HASP890 JOB({j[1]}) STATUS=(HELD)"]
        if op == "A" and j[3] == "HELD": j[3] = "INPUT"; return [f"$HASP890 JOB({j[1]}) STATUS=(AWAITING EXECUTION)"]
        if op == "C" and j[3] in ("INPUT", "ACTIVE", "HELD"): j[3] = "OUTPUT"; return [f"$HASP812 JOB {j[1]} CANCELLED"]
        if op == "P" and j[3] == "OUTPUT": S.jobs.remove(j); return [f"$HASP250 {j[1]} PURGED"]
        return [f"$HASP003 RC=(24),$%sJ - JOB {j[1]} IN WRONG STATE ({j[3]})" % op]
    mm = re.match(r"^SETPROG APF,(ADD|DELETE),DSNAME=([\w.]+),(?:VOLUME=(\w+)|SMS)$", c)
    if mm:
        if mm.group(1) == "ADD": APF.append(mm.group(2)); return [f"CSV410I DATA SET {mm.group(2)} ADDED TO APF LIST"]
        if mm.group(2) in APF: APF.remove(mm.group(2)); return [f"CSV411I DATA SET {mm.group(2)} DELETED FROM APF LIST"]
        return ["CSV412E DATA SET NOT FOUND IN APF LIST"]
    if re.match(r"^T SMF=\w\w$", c): return [f"IEE252I MEMBER SMFPRM{c[-2:]} FOUND IN SYS1.PARMLIB", "IEE536I SMF VALUE 00 NOW IN EFFECT"]
    if c.startswith("$DJOBCLASS(A)"):
        return [f"$HASP837 JOBCLASS(A) ACTIVE=YES,BLP={S.blp},COMMAND=DISPLAY,CONDPUR=NO,HOLD=NO,MSGLEVEL=(0,0),TIME=(0,15)"]
    mm = re.match(r"^\$TJOBCLASS\(A\),BLP=(YES|NO)$", c)
    if mm: S.blp = mm.group(1); return [f"$HASP837 JOBCLASS(A) BLP={S.blp}"]
    if c == "$DSPOOL": return ["$HASP893 VOLUME(SPOOL1) STATUS=ACTIVE,PERCENT=3", "$HASP646 3.1 PERCENT SPOOL UTILIZATION"]
    if c == "$DI": return [f"$HASP892 INIT({i}) STATUS=ACTIVE,CLASS=A" for i in range(1, 4)]
    if c == "$DQ": return [f"$HASP608 {j[1]} {j[0]} ON {j[3]}" for j in S.jobs if j[2] != "STC"] or ["$HASP608 QUEUE EMPTY"]
    t0 = t
    if c == "D C": return [f"IEE889I {t0} CONSOLE DISPLAY", " MSG: CURR=0 LIM=1500 RPLY: CURR=1 LIM=999 SYS=MVSH PFK=00", " CONSOLE  ID  --------------- SPECIFICATIONS ---------------", " MASTER   01  COND=M AUTH=MASTER AREA=Z", " 0700     00  COND=A AUTH=ALL"]
    if c == "D C,N": return [f"IEE889I {t0} CONSOLE DISPLAY", " INACTIVE CONSOLES: NONE DEFINED"]
    if c == "D GRS,C": return [f"ISG343I {t0} GRS STATUS", " NO ENQ/DEQ CONTENTION EXISTS"]
    if c == "D M=STOR": return [f"IEE174I {t0} DISPLAY M", " REAL STORAGE STATUS", " ONLINE-NOT RECONFIGURABLE  0M-256M", " ONLINE-RECONFIGURABLE      NONE"]
    if c == "D J,L": return [f"IEE115I {t0} JOBS", " ACTIVE BATCH JOBS"] + [f" {x[0]:8s} {x[1]}" for x in S.jobs if x[3] == "ACTIVE" and x[2] != "STC"] + [" NONE" if not any(x[3] == "ACTIVE" and x[2] != "STC" for x in S.jobs) else ""]
    if c == "D TS,L": return [f"IEE115I {t0} TS USERS", " 1 USERS  IBMUSER"]
    if c == "D SMF": return [f"IEE949I {t0} SMF DATA SETS", " NAME          VOLSER SIZE(BLKS) %FULL STATUS", " P-SYS1.MAN1   SMF001   50000      4 ACTIVE", " S-SYS1.MAN2   SMF002   50000      0 ALTERNATE"]
    if c == "D SMF,O": return [f"IEE967I {t0} SMF PARAMETERS", " MEMBER = SMFPRM00", " ACTIVE -- DSNAME(SYS1.MAN1,SYS1.MAN2) INTVAL(30) SYS(NOTYPE(14,15))"]
    if c == "D SYMBOLS": return [f"IEA007I STATIC SYSTEM SYMBOL VALUES", " &SYSNAME.  = \"MVSH\"", " &SYSCLONE. = \"SH\"", " &SYSPLEX.  = \"LOCAL\""]
    if c == "D OPDATA": return [f"IEE603I {t0} OPDATA DISPLAY", " PREFIX OWNER SYSTEM SCOPE REMOVE FAILDSP", " $      JES2  MVSH   SYSTEM NO     SYSPURGE"]
    if c == "D PROG,EXIT": return [f"CSV460I {t0} PROG,EXIT DISPLAY", " NO EXITS DEFINED"]
    if c == "DUMPDS": return ["IEE855I DUMPDS COMMAND RESPONSE", " SYS1.DUMP DATA SET STATUS", " SYS1.DUMP00 AVAILABLE   SYS1.DUMP01 AVAILABLE"]
    if c.startswith("SETIOS MIH"): return ["SETIOS MIH ACCEPTED - MIH TIME INTERVAL UPDATED"]
    mm = re.match(r"^\$VS,'?(.*?)'?$", c)
    if mm: return ["$HASP000 OK - COMMAND PASSED TO MVS"] + con(mm.group(1))
    if c in ("HELP", "?"):
        return ["OPERATOR: D T | D IPLINFO | D M=CPU | D A,L | D U,,,0A80,4 | V addr,ONLINE|OFFLINE | M addr,VOL=(SL,vol)",
                "         D R,L | R nn,text | D PROG,APF | D PROG,LNKLST | D PARMLIB | D ASM | S/P/C/F name",
                "JES2:     $DJOBCLASS(A) | $TJOBCLASS(A),BLP=YES | $DSPOOL | $DI | $DQ | $HJ(n) $AJ(n) $CJ(n) $PJ(n) $DJ(n)",
                "REF:      D C | D GRS,C | D M=STOR | D J,L | D TS,L | D SMF[,O] | D SYMBOLS | D OPDATA | D PROG,EXIT | DUMPDS | $VS,'cmd'",
                "SYSPROG:  SETPROG APF,ADD,DSNAME=x,VOLUME=v | T SMF=00   (SMP/E and IPL have own screens)"]
    return [f"IEE305I {c.split()[0] if c else ''} COMMAND INVALID"]

def tso(c):
    if c == "READY" or not c: return []
    if c.startswith("LISTC"):
        lv = re.search(r"LEVEL\((\w+)\)", c); L = lv.group(1) if lv else ""
        r = [f"IDC0001I  LISTCAT  LEVEL({L})"] + [f"NONVSAM ------- {k}" for k in CAT if k.startswith(L)]
        return r + ["READY"]
    mm = re.match(r"^LISTDS '?([\w.]+)'?", c)
    if mm:
        k = mm.group(1)
        return ([k, "--RECFM-LRECL-BLKSIZE-DSORG", "  FB    80    3120    PO", f"--VOLUMES--  {S.dev[CAT[k]][1]}"] if k in CAT else [f"DATASET {k} NOT IN CATALOG"]) + ["READY"]
    mm = re.match(r"^SUB(?:MIT)? '?[\w.]*\(?(\w+)\)?'?$", c)
    if mm:
        n = mm.group(1); jid = f"JOB{S.jn:05d}"; S.jn += 1; S.jobs.append(["IBMUSER" + n[:1], jid, "A", "INPUT"])
        sysmsg(f"$HASP100 {jid} ON INTRDR   {n}"); return [f"IKJ56250I JOB IBMUSER{n[:1]}({jid}) SUBMITTED", "READY"]
    if c in ("TIME",): return [f"IKJ56650I TIME-{now()[0]} PM. CPU-00:00:01 SERVICE-1500 SESSION-00:05:12", "READY"]
    if c == "STATUS": return ["IBMUSER-" + j[1] + "-EXECUTING" for j in S.jobs if j[3] == "ACTIVE"][:1] + ["READY"]
    if c == "HELP": return ["TSO: LISTC LEVEL(IBMUSER) | LISTDS 'dsn' | SUBMIT 'IBMUSER.JCL(AWSSL)' | TIME | STATUS", "READY"]
    return [f"IKJ56500I COMMAND {c.split()[0]} NOT FOUND", "READY"]

def sdsf(c):
    QN = {"INPUT": "INPUT", "ACTIVE": "EXEC", "OUTPUT": "PRINT", "HELD": "HELD"}
    if c in ("ST", "DA"):
        return ["NP  JOBNAME  JOBID    OWNER    PRTY QUEUE   C  POS"] + [f" {x[0]:8s} {x[1]:8s} IBMUSER  1   {QN[x[3]]:6s} {x[2][:1]}  " for x in S.jobs]
    if c == "O": return ["NP  JOBNAME  JOBID    OWNER    C  DEST"] + [f" {x[0]:8s} {x[1]:8s} IBMUSER  A  LOCAL" for x in S.jobs if x[3] == "OUTPUT"]
    if c == "I": return ["NP  NAME   STATUS  CLASS  JOBNAME"] + [f" INIT{k}  {'ACTIVE' if any(x[3]=='ACTIVE' and x[2]!='STC' for x in S.jobs) and k==1 else 'DRAINED' if k==3 else 'INACT':7s} A      " + (next((x[0] for x in S.jobs if x[3] == 'ACTIVE' and x[2] != 'STC'), "") if k == 1 else "") for k in (1, 2, 3)]
    if c == "PR": return ["PRINTER1  ACTIVE  CLASS=A  FORMS=STD", "PRINTER2  INACTIVE"]
    if c == "H": return ["HELD JOBS:"] + [f" {x[0]} {x[1]}" for x in S.jobs if x[3] == "HELD"] or ["NONE"]
    if c == "LOG": return S.syslog[-18:]
    mm = re.match(r"^S (JOB\d+)$", c)
    if mm:
        j = next((x for x in S.jobs if x[1] == mm.group(1)), None)
        if not j: return ["ISF002E JOB NOT FOUND"]
        return [f"JES2 JOB LOG  {j[0]} {j[1]}"] + ([l for l in S.syslog if j[0] in l] or ["(no messages yet)"])
    mm = re.match(r"^([CP]) (JOB\d+)$", c)
    if mm:
        return con(f"${mm.group(1)}J({mm.group(2)[3:]})")
    return ["ISF002E INVALID PRIMARY COMMAND - " + c]

def smpe(c):
    S.ok = False; st_ = S.smp["USR0001"]; z = S.zone
    m = re.match(r"^SET BDY\((\w+)\)$", c)
    if m:
        if m.group(1) in ("GLOBAL", "MVST100", "MVSTD"): S.zone = m.group(1); S.ok = True; return [f"SET BOUNDARY ZONE = {m.group(1)}", "RETURN CODE 00"]
        return ["ZONE NOT DEFINED IN GLOBAL ZONE - ZONES: GLOBAL MVST100 (target) MVSTD (dlib)"]
    if c == "HELP": return ["SET BDY(GLOBAL|MVST100|MVSTD) | RECEIVE S(USR0001) | APPLY S(USR0001) [CHECK] | ACCEPT S(USR0001) [CHECK]", "RESTORE S(USR0001) | REJECT S(USR0001) | LIST SYSMOD(USR0001)", "Flow: GLOBAL receive -> MVST100 apply -> MVSTD accept"]
    if c.startswith("LIST SYSMOD"): S.ok = True; return [f"SYSMOD  USR0001  TYPE=USERMOD  STATUS={st_}  ZONE={z}", "  ++USERMOD(USR0001). ++VER(Z038). ++MOD(DUMMY1) from IEFBR14"]
    if c.startswith("REPORT "): S.ok = True; return [f"REPORT PROCESSING - ZONE {z}", f"  SYSMOD USR0001  STATUS={st_}", "REPORT COMPLETE. HIGHEST RETURN CODE 00"]
    m = re.match(r"^(RECEIVE|APPLY|ACCEPT|RESTORE|REJECT) S\(USR0001\)( CHECK)?$", c)
    if not m: return ["SYNTAX ERROR - type HELP"]
    op, chk = m.group(1), bool(m.group(2))
    need = {"RECEIVE": ("GLOBAL", ["NONE"]), "REJECT": ("GLOBAL", ["RECEIVED"]), "APPLY": ("MVST100", ["RECEIVED"]),
            "RESTORE": ("MVST100", ["APPLIED"]), "ACCEPT": ("MVSTD", ["APPLIED", "RECEIVED"])}[op]
    if z != need[0]: return [f"{op} ERROR RC=12: BOUNDARY ZONE MUST BE {need[0]} (now {z}) - use SET BDY({need[0]})"]
    if st_ not in need[1]: return [f"{op} ERROR RC=08: SYSMOD USR0001 STATUS IS {st_} - NOT ELIGIBLE FOR {op}"]
    S.ok = True
    if chk: return [f"{op} CHECK: USR0001 WOULD BE PROCESSED. NO UPDATES MADE.", "RETURN CODE 00"]
    new = {"RECEIVE": "RECEIVED", "APPLY": "APPLIED", "ACCEPT": "ACCEPTED", "RESTORE": "RECEIVED", "REJECT": "NONE"}[op]; S.smp["USR0001"] = new
    extra = {"RECEIVE": ["SYSMOD USR0001 RECEIVED INTO GLOBAL ZONE SMPPTS"], "APPLY": ["MODULE DUMMY1 LINK-EDITED INTO SYS1.LINKLIB", "SYSMOD USR0001 APPLIED"], "ACCEPT": ["SYSMOD USR0001 ACCEPTED INTO DLIB, SMPPTS ENTRY REMOVED"], "RESTORE": ["DUMMY1 REMOVED FROM SYS1.LINKLIB - SYSMOD RESTORED"], "REJECT": ["SYSMOD REJECTED"]}[op]
    return [f"{op} PROCESSING STARTED"] + extra + [f"{op} PROCESSING COMPLETE. HIGHEST RETURN CODE 00"]

def ipl(c):
    S.ok = False; P = S.parm
    m = re.match(r"^LIST (\w+)$", c)
    if m:
        if m.group(1) not in P: return [f"IEE... MEMBER {m.group(1)} NOT IN SYS1.PARMLIB (members: {', '.join(P)})"]
        S.ok = True; return [f"SYS1.PARMLIB({m.group(1)})"] + [f"  {k}={v}" for k, v in P[m.group(1)].items()]
    m = re.match(r"^SET (\w+),(\w+)=(\S+)$", c)
    if m:
        if m.group(1) in P: P[m.group(1)][m.group(2)] = m.group(3); S.chg = True; S.ok = True; return [f"{m.group(1)}: {m.group(2)}={m.group(3)} SAVED (takes effect at next IPL)"]
        return ["MEMBER NOT FOUND"]
    m = re.match(r"^IPL ([0-9A-F]{3,4})(?:,(.*))?$", c)
    if m:
        a = m.group(1).zfill(4); op = m.group(2) or ""
        if a not in S.dev or S.dev[a][2] != "ONLINE" or S.dev[a][1] != "SYSRES": return ["HHC00811E IPL DEVICE NOT A BOOTABLE SYSRES"]
        S.ok = True; y = P["IEASYS00"]; r = [f"IPL FROM {a}  LOADPARM=0A8000M1", f"IEA371I SYS1.PARMLIB ON {a} SELECTED FOR IPL PARAMETERS", "IEE252I MEMBER IEASYS00 FOUND IN SYS1.PARMLIB"]
        r += ["CLPA REQUESTED - PLPA REBUILT FROM LPALST" if "CLPA" in op else "WARM START - PLPA REUSED (LPA changes need CLPA)", f"SYSNAME={y['SYSNAME']} MAXUSER={y['MAXUSER']} APF={y['APF']} LNK={y['LNK']} SMF={y['SMF']}"]
        r += (["PARMLIB CHANGES NOW IN EFFECT"] if S.chg else []) + ["IEE252I MEMBER COMMND00 FOUND - S JES2", "$HASP426 SPECIFY OPTIONS - JES2 SP 4.1.0", "IEE136I SYSTEM IPL COMPLETE"]
        S.chg = False; S.jobs = [["JES2", "STC00001", "STC", "ACTIVE"], ["MSTR", "STC00002", "STC", "ACTIVE"]]; S.wtor = {"01": "$HASP426 SPECIFY OPTIONS - JES2 SP 4.1.0 (reply NOREQ)"}; S.syslog = ["IPL COMPLETE"]
        return r
    return ["LIST member | SET member,KEY=VALUE | IPL 0A80[,CLPA]   (members: IEASYS00 SMFPRM00 COMMND00)"]

ZYAML = ["zowe:", "  runtimeDirectory: /var/lpp/zowe", "  workspaceDirectory: /global/zowe/workspace", "  setup:", "    dataset:", "      prefix: ZWE", "      proclib: USER.PROCLIB", "    security:", "      product: RACF", "    vsam:", "      mode: NONRLS", "    certificate:", "      type: PKCS12"]
ZSUB = ["mvs", "vsam", "apfauth", "security", "certificate", "stc"]

def zowe(c):
    c = c.lower().strip(); Z = S.zw; S.ok = False; tk = c.split()
    if not tk: return []
    if c in ("help", "?"): return ["USS: pwd | ls | cat zowe.yaml | export ZWE_CLI_PARAMETER_CONFIG=/var/lpp/zowe/zowe.yaml", "zwe -h | zwe install -c zowe.yaml | zwe init [mvs|vsam|apfauth|security|certificate|stc] | zwe start | zwe stop", "zowe zosmf check status | zowe jobs list jobs | zowe jobs submit ds \"ibmuser.jcl(awssl)\" | zowe files list ds \"ibmuser.*\""]
    m = re.match(r"^export zwe_cli_parameter_config=(\S+)$", c)
    if m: Z["env"] = m.group(1); S.ok = True; return []
    if c == "pwd": S.ok = True; return ["/u/ibmuser"]
    if c == "ls": S.ok = True; return ["zowe.yaml  zowe-2.x.pax  zowe-runtime"]
    if c in ("cat zowe.yaml", "cat ./zowe.yaml"): S.ok = True; return ZYAML
    if tk[0] == "zwe":
        sub = tk[1] if len(tk) > 1 else "-h"
        conf = next((tk[i + 1] for i, x in enumerate(tk[:-1]) if x in ("-c", "--config")), Z["env"])
        if sub in ("-h", "--help"): S.ok = True; return ["zwe - Zowe z/OS server command", "  install   install Zowe MVS data sets", "  init      initialize (mvs vsam apfauth security certificate stc)", "  start     start Zowe (ZWESLSTC)", "  stop      stop Zowe"]
        if sub not in ("install", "init", "start", "stop"): return [f"zwe: unknown command {sub}"]
        if not conf: return ["Error: zowe.yaml not specified. Use -c /path/zowe.yaml or export ZWE_CLI_PARAMETER_CONFIG"]
        if sub == "install": Z["inst"] = True; S.ok = True; return [">> INSTALL ZOWE MVS DATA SETS", "  ZWE.SZWEAUTH  ZWE.SZWEEXEC  ZWE.SZWESAMP  ZWE.SZWELOAD  installed", "Next step: zwe init"]
        if not Z["inst"]: return ["Error: run zwe install first (MVS data sets missing)"]
        if sub == "init":
            part = [tk[2]] if len(tk) > 2 and tk[2] in ZSUB else ZSUB
            for p in part: Z["init"].add(p)
            S.ok = True; return [f">> INITIALIZE {p.upper()}  ... done" for p in part]
        if sub == "start":
            if set(ZSUB) - Z["init"]: return ["Error: zwe init incomplete - missing: " + ", ".join(sorted(set(ZSUB) - Z["init"]))]
            if not any(x[0] == "ZWESLSTC" and x[3] == "ACTIVE" for x in S.jobs):
                S.jobs.append(["ZWESLSTC", f"STC{S.jn:05d}", "STC", "ACTIVE"]); S.jn += 1; sysmsg("IEF403I ZWESLSTC - STARTED")
            S.ok = True; return ["Starting Zowe...", "S ZWESLSTC issued - check console: D A,L", "API Mediation Layer, App Server, Zowe desktop on configured ports"]
        for x in S.jobs:
            if x[0] == "ZWESLSTC" and x[3] == "ACTIVE": x[3] = "OUTPUT"; sysmsg("IEF404I ZWESLSTC - ENDED"); S.ok = True; return ["Zowe stopped (P ZWESLSTC)"]
        return ["Zowe is not running"]
    if tk[0] == "zowe":
        if c == "zowe zosmf check status": S.ok = True; return ["The user \"IBMUSER\" successfully connected to z/OSMF.", "zosmf_port: 443", "z/OSMF REST services reachable"]
        if c == "zowe jobs list jobs": S.ok = True; return ["JOBNAME   JOBID     STATUS"] + [f"{x[0]:9s} {x[1]:9s} {x[3]}" for x in S.jobs]
        m = re.match(r"^zowe files list ds \"?([\w.*]+)\"?$", c)
        if m: S.ok = True; q = m.group(1).upper().rstrip("*").rstrip("."); return [k for k in CAT if k.startswith(q)] or ["(no data sets)"]
        m = re.match(r"^zowe jobs submit ds \"?[\w.]*\(?(\w+)\)?\"?$", c)
        if m: S.ok = True; jid = f"JOB{S.jn:05d}"; S.jn += 1; S.jobs.append(["IBMUSER" + m.group(1)[:1].upper(), jid, "A", "INPUT"]); return [f"jobname: IBMUSER{m.group(1)[:1].upper()}  jobid: {jid}  status: INPUT"]
        return ["zowe: command or profile not recognised - type help"]
    return [f"-sh: {tk[0]}: not found"]

def check(c):
    S.cmds.append(c)
    for i, e in enumerate(EX):
        if i not in S.done and S.ok and re.match(e[3], c):
            ok = True
            if e[3].endswith("P TESTSTC$") and not any(j[0] == "TESTSTC" for j in S.jobs): ok = False
            if ok: S.done.add(i)
    if S.lc:
        S.done |= {i for i, e in enumerate(EX) if e[3] == r'^LIFECYCLE$'}

def screen(key, handler, prompt, banner=None):
    lines = ([banner] if banner else []) + S.log.setdefault(key, [])
    body = "\n".join(html.escape(x) for x in lines)
    st.markdown(f"<div class='wrap'><div class='crt'>{body}</div></div>", unsafe_allow_html=True)
    with st.form(key + "f", clear_on_submit=True):
        c1, c2 = st.columns([8, 1])
        v = c1.text_input("cmd", placeholder=prompt, label_visibility="collapsed", key=key + "i")
        go = c2.form_submit_button("ENTER")
    if go and v.strip():
        c = v.strip() if key == "tso" else v.strip().upper()
        S.log[key].append((">" if key != "con" else "") + c)
        S.ok = True; tick(); S.log[key] += handler(c.upper()); check(c.upper()); st.rerun()

def tools_lab():
    st.subheader("HERCULES TAPE / DASD TOOLS LAB (your uploaded files)")
    n = st.selectbox("Utility", list(TOOLS))
    f, title, out = TOOLS[n]; st.write(title)
    p = os.path.join(HERE, "files", f)
    src = open(p, errors="replace").read() if os.path.exists(p) else "(file missing)"
    c1, c2 = st.columns(2)
    with c1:
        st.caption("SOURCE / JCL (first 60 lines of uploaded file)")
        st.markdown("<div class='wrap' style='height:380px;flex-direction:column'><div class='crt' style='font-size:11px'>" + html.escape("\n".join(l[:78] for l in src.splitlines()[:60])) + "</div></div>", unsafe_allow_html=True)
    with c2:
        st.caption("SIMULATED JOB OUTPUT (SDSF)")
        if st.button(f"SUBMIT {n}"):
            tso(f"SUBMIT 'IBMUSER.JCL({n})'"); sysmsg(f"IEF142I {n} STEP - STEP WAS EXECUTED - COND CODE 0000")
            if n == "AWSWRITE" and S.blp != "YES": S.out = [f"IEF450I {n} GO - ABEND=S913 BLP NOT ALLOWED IN CLASS A", "FIX: $TJOBCLASS(A),BLP=YES on console, then resubmit"]
            elif n in ("AWSWRITE",) and S.dev["0580"][2] != "ONLINE": S.out = ["IEF233A M 0580,AWS001 - mount tape first (M 0580,VOL=(SL,AWS001))"]
            elif n == "CCKDLOAD" and S.dev["0A84"][2] != "OFFLINE": S.out = ["CCKD0004E UNIT 0A84 MUST BE OFFLINE - use V 0A84,OFFLINE"]
            else: S.out = [f"IEF142I {n} - STEP WAS EXECUTED - COND CODE 0000"] + out; check(f"RUN:{n}")
            S.outn = n
        o = getattr(S, "out", ["(submit to see output)"])
        st.markdown("<div class='wrap' style='height:380px;flex-direction:column'><div class='crt'>" + html.escape("\n".join(o)) + "</div></div>", unsafe_allow_html=True)
    if n == "AWSWRITE": st.info("Exercise: Console must run $TJOBCLASS(A),BLP=YES and M 0580,VOL=(SL,AWS001) before this job succeeds.")
    if n == "CCKDLOAD": st.info("Exercise: Console must run V 0A84,OFFLINE first.")
    zp = os.path.join(HERE, "files", "zzsacard.bin")
    if os.path.exists(zp):
        st.caption(f"zzsacard.bin ({os.path.getsize(zp)} bytes) = stand-alone dump IPL card deck. Simulated IPL from reader 000C:")
        if st.button("IPL 000C (SADMP card deck)"):
            S.out = ["HHC00001I IPL 000C", "AMDSA001I SAD INITIALIZED", "AMDSA002A SPECIFY OUTPUT DEVICE (tape 0580) ->", "AMDSA010I DUMP COMPLETE, 128M, WAIT STATE 0000"]; st.code("\n".join(S.out))

def exercises():
    st.subheader("SYSPROG EXERCISES  (%d / %d complete)" % (len(S.done), len(EX)))
    st.progress(len(S.done) / len(EX))
    mods = sorted({e[0] for e in EX}, key=[e[0] for e in EX].index)
    for m in mods:
        with st.expander(m, expanded=True):
            for i, e in enumerate(EX):
                if e[0] == m:
                    st.markdown(f"{'[X]' if i in S.done else '[ ]'} **{e[1]}** - {e[2]}  \n_Hint:_ `{e[4]}`  _Ref:_ {e[5]}")

def reference():
    st.subheader("REFERENCE - docs this simulator is modeled on")
    st.markdown("**IBM MVS System Commands:** https://www.ibm.com/docs/SSLTBW_3.1.0/com.ibm.zos.v3r1.ieag100/cmdref.htm  \n"
      "**SMP/E User's Guide:** https://www.ibm.com/docs/en/SSLTBW_2.1.0/com.ibm.zos.v2r1.gim3000/toc.htm  (RECEIVE-APPLY-ACCEPT, CHECK facility, REPORT)  \n"
      "**SMP/E Commands (SA23-2275) / Messages, Codes, Diagnosis (GA32-0883, GIM prefix)**  \n"
      "**Zowe z/OS install (zwe install, init, start, stop; zowe.yaml; ZWESLSTC):** https://docs.zowe.org/stable/user-guide/install-zowe-zos-convenience-build/  \n"
      "**Zowe install overview:** https://docs.zowe.org/stable/user-guide/installandconfig/  \n"
      "**Hercules:** http://www.hercules-390.org")
    st.markdown("Commands follow these docs; message wording is modeled, not copied. MVS 3.8j (TK5) lacks some z/OS commands (D PROG, SETPROG, Zowe).")

with st.sidebar:
    st.markdown("### MVS SYSPROG SIM")
    mod = st.radio("MODULE", ["Operator Console", "TSO READY", "SDSF / JES2 Log", "SMP/E", "IPL / PARMLIB", "Zowe (USS)", "Tools Lab", "Exercises", "Reference"])
    st.write(f"Done: {len(S.done)}/{len(EX)}")
    if st.button("RESET SYSTEM"): S.clear(); st.rerun()
st.markdown("# MVS 3.8J / HERCULES TK5 - SYSPROG TRAINER")
if mod == "Operator Console":
    screen("con", con, "ENTER MVS COMMAND (HELP for list)", "IEE041I THE SYSTEM LOG IS NOW ACTIVE\nIEE600I CONSOLE 0700 ACTIVE   SYSTEM=MVSH")
elif mod == "TSO READY": screen("tso", tso, "TSO command, e.g. LISTC LEVEL(IBMUSER)", "IKJ56700A ENTER USERID - IBMUSER\nWELCOME TO TSO")
elif mod == "SDSF / JES2 Log": screen("sdsf", sdsf, "ST, DA, LOG, H")
elif mod == "SMP/E": screen("smpe", smpe, "SMP/E command (HELP)", f"SMP/E DIALOG - SYSMOD USR0001 (dummy IEFBR14 USERMOD)  Zones: GLOBAL, MVST100, MVSTD")
elif mod == "IPL / PARMLIB": screen("ipl", ipl, "LIST IEASYS00 | SET IEASYS00,MAXUSER=300 | IPL 0A80,CLPA", "SYS1.PARMLIB EDITOR / IPL PANEL")
elif mod == "Zowe (USS)": screen("zowe", zowe, "USS: zwe install -c ./zowe.yaml | zowe jobs list jobs | help", "Zowe z/OS runtime - OMVS shell   IBMUSER@MVSH:/u/ibmuser\nFollow the docs order: install -> init -> start (type help)")
elif mod == "Tools Lab": tools_lab()
elif mod == "Exercises": exercises()
else: reference()
