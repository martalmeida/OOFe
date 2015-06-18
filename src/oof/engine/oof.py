import matplotlib
matplotlib.use('agg')

import time
import os
import glob
import sys
from subprocess import Popen, PIPE

from okean import dateu
from okean.cookbook import relativepath
from okean.roms.roms_tools import is_roms_out_ok

import op_tools as opt
import op_plot
import send_email

CONF='oof.conf'


# add apptools to path:
import sys
p=os.path.realpath(os.path.dirname(__file__))
appDir=os.path.join(p,'../aux/apptools')
if os.path.isdir(appDir): sys.path.append(appDir)

def find_last(type='rout',FA='a',nest=0,cf=CONF):
  kargs={'date':'*','FA':FA,'nest':nest,'cf':cf}
  if type=='rout':
    name=opt.nameof('out',type,**kargs)
  elif type=='ini':
    name=opt.nameof('in', type,**kargs)
  elif type=='rst':
    name=opt.nameof('out',type,**kargs)

  fs=glob.glob(name)
  if fs:
    L=name.index('*')
    date=fs[0][L:L+8]
    file=fs[0]
    for i in range(1,len(fs)):
      if fs[i][L:L+8]>date:
        date=fs[i][L:L+8]
        file=fs[i]

    return dateu.parse_date(date), file
  else:
    return '',''

def find_prev(cf=CONF):
  type='rout'
  date, file=find_last(type,cf=cf)
  if not date:
    type='ini'
    date, file=find_last(type,cf=cf)
    if date: date=dateu.next_date(date,-1)

  return date, file, type


def gen_ini(date,FA='a',nest=0,cf=CONF):
  date=dateu.parse_date(date)
  dateRst=dateu.next_date(date,-1)


  rst=opt.nameof('out','rst',date=dateRst,FA=FA,nest=nest,cf=cf)

  ini=opt.nameof('in', 'ini',date=date,FA=FA,nest=nest,cf=cf)
  err=False
  isFatal=False

  if os.path.isfile(ini):
    err='INI file already exists: ....%s' % ini[-30:]
    isFatal=False
  elif not os.path.isfile(rst):
    err='RST file not found: %s' % rst
    isFatal=True
  else:
    y,m,d=date.year,date.month,date.day
    model=opt.get_conf(cf,'MODEL','name',type=str)[nest]
    if model.lower()=='roms-agrif' and (m,d)==(1,1):
      # copy and change time to 0:
      err=opt.restart_ini(rst,ini)
      if err: isFatal=True
    else:
      # do not copy, create link:
      try:
        os.symlink(rst,ini)
      except OSError, e:
        err=e.strerror
        isFatal=True

  return err, isFatal, ini


def check_atm(date,FA,wait=3600,cf=CONF):
  atmPath = opt.pathof(cf,'external','atm')
  atmData=opt.atm_info(cf)['data']
  npred=opt.n_pred(cf)
  if atmData=='wrf':
    from ompy.roms import atmblk_forcing as bfrc
    ir=bfrc.is_ready_wrf(date,FA,wrfpath=atmPath)
  elif atmData=='gfs':
    from okean.datasets.gfs import is_ready as is_ready_gfs
    ir=is_ready_gfs(atmPath,date,FA,npred)

  if ir is True:
    print 'atm ok at check'
    return True

  now   = dateu.currday()
  tdiff = now-date
  tdiff=tdiff.days+tdiff.seconds/86400.

  print "waiting for atm: %s" % FA
  if FA=='a':
    # wait till 12am today to start creating anaylysis of prev day!->tdif=1.5
    # with all atm data ok
    # if time higher, the available possible data is used.
    while tdiff < 1.5:
      time.sleep(wait)
      sys.stdout.write('.')

      now   = dateu.currday()
      tdiff = now-date
      tdiff=tdiff.days+tdiff.seconds/86400.

      if atmData=='wrf':
        ir=bfrc.is_ready_wrf(date,FA,wrfpath=atmPath)
      elif atmData=='gfs':
        ir=is_ready_gfs(atmPath,date,FA,npred)

      print "  atm data ready = %s  : %s  tdiff %6.2f"%(ir,now.isoformat(' '), tdiff)

      if ir is True: return True

  elif FA=='f':
    # if atm not data present after tdiff, forget current forecast
    while tdiff < 1.5:
      time.sleep(wait)
      sys.stdout.write('.')

      now   = dateu.currday()
      tdiff = now-date
      tdiff=tdiff.days+tdiff.seconds/86400.

      if atmData=='wrf':
        ir=bfrc.is_ready_wrf(date,FA,wrfpath=atmPath)
      elif atmData=='gfs':
        ir=is_ready_gfs(atmPath,date,FA,npred)

      print "  atm data ready = ",ir,' at ',now, tdiff

      if ir is True: return True

  return ir

def check_bc(date,FA,wait=3600,cf=CONF):
  print 'checking parent model...'
  import get_hycom
  nforec=opt.n_pred(cf)
  date1=None
  if FA=='f': date1=dateu.parse_date(dateu.next_date(date,nforec))

  ir=get_hycom.is_ready(date,date1,check1=FA=='a')

  if get_hycom.is_ready(date,date1):
    print 'bc ok at check'
    return True
  else:
    now   = dateu.currday()
    tdiff = dateu.date_diff(date,now)
    print "waiting for bc"
    while tdiff.days < 1.5:
      time.sleep(wait)
      sys.stdout.write('.')
      now   = dateu.currday()
      tdiff = dateu.date_diff(date,now)

      cond= get_hycom.is_ready(date,date1,check1=FA=='a')
      print "  bc file ready =  ",cond,' at ',now, tdiff
      if cond: return True

  return get_hycom.is_ready(date,date1,check1=FA=='a')


def check_rst(date,cf,wait=900):
  '''check rst for forecast, and wait for tdiff'''

  FA='a'
  date0=dateu.next_date(date,-1)
  rst=opt.nameof('out','rst',date=date0,FA=FA,cf=cf)
  # check also if run terminated! The rst may not have the last reccord yet!
  rout=opt.nameof('out','rout',date=date0,FA=FA,cf=cf)

  if os.path.isfile(rst) and is_roms_out_ok(rout): return True
  else:
    now   = dateu.currday()
    tdiff = dateu.date_diff(date,now)
    print "waiting for rst"
    while tdiff.days < 1.5:
      time.sleep(wait)
      sys.stdout.write('.')
      now   = dateu.currday()
      tdiff = dateu.date_diff(date,now)

      cond=os.path.isfile(rst) and is_roms_out_ok(rout)
      print "  rst file ready =  ",cond,' at ',now, tdiff
      if cond: return True

  return os.path.isfile(rst)



def gen_atmfrc(date,FA='a',nest=0,cf=CONF,quiet=True):
  date=dateu.parse_date(date)
  err=''
  isFatal=False

  fname=opt.nameof('in','blk',date=date,FA=FA,nest=nest,cf=cf)

  if os.path.isfile(fname):
    err='BLK file already exists'
    isFatal=False
  else:
    grd=opt.nameof('in','grd',cf=cf)
    atmPath = opt.pathof(cf,'external','atm')
    atmData=opt.atm_info(cf)['data']
    nforec=opt.n_pred(cf)

    if atmData=='wrf':
      cycle=366-29+dateu.mndays(date.year,date.month)
      err=bfrc.make_blk_wrf(fname,grd,date,FA,atmPath,quiet=quiet,cycle=cycle)
    elif atmData=='gfs':
      from okean.roms.inputs import surface
      if FA=='a': nforec=0
      model=opt.get_conf(cf,'MODEL','name',type=str)[nest].lower()
      surface.make_blk_gfs(atmPath,grd,fname,date,nforec=nforec,model=model,quiet=quiet)

    try:
      if err:
        err='ERROR creating bulk file ('+err+')'
        isFatal=True
    except OSError, e:
      err='ERROR creating bulk file ('+str(e)+')'
      isFatal=True
    except:
      err='ERROR creating bulk file'
      isFatal=True

  return err, isFatal, fname

def gen_tidalfrc(date,FA='a',nest=0,cf=CONF):
  from py_pack.roms import tides_forcing as tfrc
  date=dateu.parse_date(date)
  err='Not implemented yet!!'
  isFatal=True

def gen_rivfrc(date,FA='a',nest=0,cf=CONF):
  date=dateu.parse_date(date)
  err=''
  isFatal=False

  fname=opt.nameof('in','frc',date=date,FA=FA,nest=nest,cf=cf)
  grd=opt.nameof('in','grd',cf=cf)

  if os.path.isfile(fname):
    err='RIVERS file already exists'
    isFatal=False
  else:
    nforec=opt.n_pred(cf)
    import get_rivers
    date1=None
    if FA=='f': date1=dateu.parse_date(dateu.next_date(date,nforec))
    try:
      err=get_rivers.gen_frc(fname,grd,date,date1)
    except:
      err='ERROR creating rivers file'

    if err: isFatal=True

  return err, isFatal, fname


def gen_clmbry(date,FA='a',nest=0,cf=CONF,quiet=True):
  date=dateu.parse_date(date)
  err=''
  isFatal=False

  fclm=opt.nameof('in','clm',date=date,FA=FA,nest=nest,cf=cf)
  fbry=opt.nameof('in','bry',date=date,FA=FA,nest=nest,cf=cf)
  grd=opt.nameof('in','grd',cf=cf)

  if os.path.isfile(fclm) and os.path.isfile(fbry):
    err='CLMBRY files already exists'
    isFatal=False
  else:
    nforec=opt.n_pred(cf)
    import get_hycom
    # no need to check if data is ready! if not gen_clm_bry will return error!
    # anyway, cannot know if hycom data of today is analtsis or forecast!!

    date1=None
    if FA=='f': date1=dateu.parse_date(dateu.next_date(date,nforec))
    try:
      err=get_hycom.gen_clm_bry(fclm,fbry,grd,date,date1,quiet=quiet)
      if err:
        err='ERROR creating clm bry files : %s' % err
        isFatal=True
    except:
      err='ERROR creating clm bry files'
      isFatal=True


  return err, isFatal, fclm,fbry

def gen_in(date,FA='a',nest=0,cf=CONF):
  err=''
  isFatal=False

  instd=opt.nameof('in','rin0',nest=nest,FA=FA,cf=cf)
  rin  =opt.nameof('in','rin',date,FA,nest,cf=cf)

  if not os.path.isfile(instd):
    err='ERROR: standard roms in not found: %s' % instd
    isFatal=True
  else:
    try:
      s=open(instd,'r').read()

      epath,exc=opt.nameof_run(cf=cf,FA=FA)
      RUN=os.path.join(epath,exc)
      kargs={'date':date,'FA':FA,'nest':nest,'cf':cf}
      inikargs={'date':date,'FA':'a','nest':nest,'cf':cf}
      d={'grd':    relativepath(RUN, opt.nameof('in', 'grd',**kargs)),
         'frc':    relativepath(RUN, opt.nameof('in', 'frc',**kargs)),
         'blk':    relativepath(RUN, opt.nameof('in', 'blk',**kargs)),
         'clm':    relativepath(RUN, opt.nameof('in', 'clm',**kargs)),
         'bry':    relativepath(RUN, opt.nameof('in', 'bry',**kargs)),
         'ini':    relativepath(RUN, opt.nameof('in', 'ini',**inikargs)),
         'rst':    relativepath(RUN, opt.nameof('out','rst',**kargs)),
         'his':    relativepath(RUN, opt.nameof('out','his',**kargs)),
         'avg':    relativepath(RUN, opt.nameof('out','avg',**kargs)),
         'flt_in': relativepath(RUN, opt.nameof('in', 'flt',**kargs)),
         'flt':    relativepath(RUN, opt.nameof('out','flt',**kargs)),
         'sta_in': relativepath(RUN, opt.nameof('in', 'sta',**kargs)),
         'sta':    relativepath(RUN, opt.nameof('out','sta',**kargs)),
         'title':  opt.atts_info(cf)['title'],
         'appcpp': opt.atts_info(cf)['appcpp']
         }

      d['dstart']= '%d' % dateu.date_diff(date,'1970-01-01').days  # days since 19700101
      jobinfo=opt.run_sub_info(cf,date=date,FA=FA)
      kk='ntilei','ntilej'
      for k in kk: d[k]=jobinfo[k]

      for k in d.keys(): s=s.replace('#'+k.upper()+'#',d[k])

      fid=open(rin,'w')
      fid.write(s)
      fid.close()
    except:
      err='ERROR creating roms in file'
      isFatal=True

  return err,isFatal, rin


def gen_sub(date,FA,cf):
  err=''
  isFatal=False

  info=opt.run_sub_info(cf,date=date,FA=FA)

  # roms (not agrif) run cmd in serial mode is different from agrif:
  model = opt.get_conf(cf,'MODEL','name',type=str)[0].lower()
  mpi   = opt.get_conf(cf,'FLAGS','mpi')[0]
  if model=='roms' and not mpi:
    tmp=info['run_cmd'].split()
    tmp[0]=tmp[0]+' <'
    info['run_cmd']=' '.join(tmp)

  if not os.path.isfile(info['sub0']):
    err='ERROR: standard sub file not found: %s' % info['sub0']
    isFatal=True
  else:
    s=open(info['sub0']).read()

    for k in info.keys(): s=s.replace('%'+k.upper()+'%',info[k])

    f=open(info['sub'],'w')
    f.write(s)
    f.close()

  return err, isFatal, info['sub']


def on_error(sendEmail,err,emailInfo=False):
  print err
  msg='Op model STOP'
  print msg+'\n'
  if sendEmail: send_email.send(emailInfo['dest'],err,msg)#sys.stdout.content,err)


def env_vars(env):
  from os import putenv
  if env:
    for k in env.keys():
      putenv(k,env[k])

def oof(cf,plconf,date=False,last_date=False,FA='a',env=False):
  # start email notifications service:
  emailInfo=opt.email_info(cf=cf)
  sendEmail=emailInfo['send']
  #if sendEmail: sys.stdout=opt.Redirect()

  env_vars(env)
  flags=opt.flags_info(cf)

  if date: date=dateu.parse_date(date)
  if last_date: last_date=dateu.parse_date(last_date)

  if not date:
    # find date-1 for prediction:
    date,file=find_last(type='rst',cf=cf)
    if not date:
      on_error(sendEmail,'ERROR (%s): Cannot find previous file'%FA,emailInfo)
      return
    else:
      print 'Last date = %s from file %s' % (date,file)
      rout=opt.nameof('out','rout',date=date,FA='a',cf=cf)
      if is_roms_out_ok(rout):
        print 'Previous roms out is ok: %s' % rout
      else:
        on_error(sendEmail,'ERROR (%s): Last run is not ok %s : %s' % (FA,date,rout),emailInfo)
        return

  else:
    date=dateu.next_date(date,-1)

  # read dates:
  start_date,end_date=opt.dates_info(cf)
  if last_date: end_date=dateu.next_date(last_date,+1)

  while date >= start_date and date < end_date:

    # read dates again, possible update may occur.
    start_date,end_date=opt.dates_info(cf)
    if last_date: end_date=dateu.next_date(last_date,+1)

    date=dateu.next_date(date)

    # check if already runned for that date:
    # ie, check for rst and check if roms_out is ok:
    rst=opt.nameof('out','rst',date=date,FA=FA,cf=cf)
    rout=opt.nameof('out','rout',date=date,FA=FA,cf=cf)

    if os.path.isfile(rst):
      print 'Found rst file for %s: %s' % (date,rst)
      if os.path.isfile(rout):
        if is_roms_out_ok(rout):
          print '  previous roms out is ok: %s' % rout
        else:
          on_error(sendEmail,'ERROR (%s): Previous roms out is NOT ok: %s' % (FA,rout),emailInfo)
          break
      else:
        print '  roms out for %s not found: NOT CHECKED' % date

    else:

      print '\nModel will start from %s' % date

      # check for atm data for current simulation:
      if flags['atmfrc'] or flags['atmblk']:
        atmStat=check_atm(date,FA,cf=cf)
      else: atmStat=True

      ## wait for rst in case of fa==F:
      ##if FA=='f': rstStat=check_rst(date,cf=cf)
      ##else: rstStat=True
      rstStat=check_rst(date,cf=cf)

      # check for bondary data for current simulation:
      if flags['clmbry']:
        # this step may take forever !! just let us belive parent model is available
        #bcStat=check_bc(date,FA,cf=cf)
        bcStat=True
      else: bcStat=True

      now=time.strftime("%Y-%m-%d %H:%M:%S +0",time.gmtime())
      if (not atmStat is False) and (not rstStat is False) and (not bcStat is False):
        rout,dt,runErr=run(date,FA,cf=cf)
        now=time.strftime("%Y-%m-%d %H:%M:%S +0",time.gmtime())

        # check if run was ok:
        if is_roms_out_ok(rout):
          msg='NO error %s %s'%(date,FA)
          Msg='  Run %s %s finished ok [%s] dt=%6.2f' % (date,FA,now,dt)
          print Msg

          # make plots:
          if flags['plots']:
            err,savenames=op_plot.op_plt(cf,plconf,date,FA)
            if not all(e=='' for e in err):
              msg+=' --> ERROR plotting'
              print '  ERROR plotting : ',
              for e in err: print e

            if not all(e=='' for e in savenames):
              for sv in savenames:
                print '  Saved plot  '+sv

        elif runErr:
          on_error(sendEmail,'ERROR (%s): Run %s returned the error msg: %s' % (FA,date,runErr),emailInfo)
          break
        else:
          on_error(sendEmail,'ERROR (%s): Run %s finished with ERROR [%s] dt=%6.2f' % (FA,date,now,dt),emailInfo)
          break

      elif atmStat is False:
          Msg='ERROR (%s): Run %s cannot run (atm data missing) ERROR [%s]' % (FA,date,FA,now)
          if FA=='a':
            on_error(sendEmail,Msg,emailInfo)
            break
          else:
            msg='ERROR: atm data missing'
            print Msg

      elif rstStat is False:
        msg='ERROR: rst data missing'
        Msg='ERROR (%s): Run %s cannot run (atm data missing) ERROR [%s]' % (FA,date,now)
        print Msg


      print '\n'
      if sendEmail: send_email.send(emailInfo['dest'],Msg,msg)


def start_status_log(flog,islocal,date,FA,info,subp,t0):

  t0str=time.strftime("%Y-%m-%d %H:%M:%S +0",time.gmtime(t0))

  ipid=open(flog,'w')

  ipid.write('[job/process id]\n')
  try:
    ipid.write('%d\n' % subp.pid)
  except:
    ipid.write('%s\n' % subp)

  ipid.write('[queue/local]\n')
  if islocal:
    ipid.write('%s\n' % 'local')
  else:
    ipid.write('%s\n' % 'queue')

  ipid.write('[date]\n')
  ipid.write('%s\n' % date)

  ipid.write('[FA]\n')
  ipid.write('%s\n' % FA)

  ipid.write('[tstart]\n')
  ipid.write('%d %s\n' % (t0,t0str))
  ipid.close()


def stop_status_log(flog,date,FA,t1,dt,texc):
  t1str=time.strftime("%Y-%m-%d %H:%M:%S +0",time.gmtime(t1))

  ipid=open(flog,'a')

  ipid.write('[tend]\n')
  ipid.write('%d %s\n' % (t1,t1str))

  ipid.write('[dt (min)]\n')
  ipid.write('%.2f\n' % dt)

  ipid.write('[time exc start]\n')
  ipid.write('%.2f\n' % texc[0])

  ipid.write('[time exc end]\n')
  ipid.write('%.2f\n' % texc[1])

  ipid.close()


def __run_queue(fsub,date,FA,cf):
  info=opt.run_sub_info(cf,date=date,FA=FA)

  # submit:
  c=Popen((info['qsub'],fsub),stdout=PIPE,stderr=PIPE)
  o,e=c.communicate()

  if e: return 1,info['rout'],0
  else: status=0

  subp=o.strip()
  if subp.find('.'): jobid=subp[:subp.find('.')]
  else: jobid=subp

  t    = 60 # check every min
  tmax = 24 # max allowed time in queue, 24 h
  dt   = 0

  t0=time.time()
  flog=opt.nameof_log(date=date,FA=FA,cf=cf)
  start_status_log(flog,False,date,FA,info,jobid,t0)

  def end_indicator(info,retTime=False):
    if not os.path.isfile(info['indicator']):
      if retTime: return 0,0
      else: return False

    lines=open(info['indicator']).readlines()
    if len(lines)==2:
      t0=int(lines[0])
      t1=int(lines[1])
      dt=(t1-t0)/60. # min
      if retTime: return t0,t1

      if not dt: return -1
      else: return dt

    else:
      if retTime:
        try: return int(lines[0]),0
        except: return 0,0

      else: return False


  while not end_indicator(info) and dt <=tmax:
    time.sleep(t)
    dt=(time.time()-t0)/3600.

  if dt>tmax and not end_indicator(info):
    status=9
    # try to remove job from queue:
    c=Popen((info['qdel'],jobid),stderr=PIPE)
    o,e=c.communicate()
    if e: print 'ERROR removing job : qdel ',jobid
    else: print 'Job ',jobid,' removed from queue'


  texc  = end_indicator(info,retTime=True)
  dtexc = end_indicator(info,retTime=False)
  stop_status_log(flog,date,FA,time.time(),dt*60.,texc)

  # indicator file no longer needed:
  if os.path.isfile(info['indicator']): os.remove(info['indicator'])

  return status,info['rout'],dtexc


def __run_local(date,FA,cf):
  info=opt.run_local_info(cf,date=date,FA=FA)

  # current folder:
  currDir=os.path.realpath(os.path.curdir)

  # popen args:
  if isinstance(info['exc'],basestring):
    args=info['exc'],info['rin']
  else: # list ...
    args=info['exc']+[info['rin']]

  # pid log filename:
  flog=opt.nameof_log(date=date,FA=FA,cf=cf)

  # go to run dir:
  os.chdir(info['run_dir'])

  t0=time.time()

  out=open(info['rout'],'w')
  subp=Popen(args,stdout=out)

  start_status_log(flog,True,date,FA,info,subp,t0)

  status=subp.wait()

  t1=time.time()
  dt=(t1-t0)/60.
  stop_status_log(flog,date,FA,t1,dt,[t0,t1])

  # set rout with full path before changing folder:
  info['rout']=os.path.realpath(info['rout'])

  # go back to original folder:
  os.chdir(currDir)

  return status,info['rout'],dt



def run(date,FA='a',cf=CONF):
  def check_gen(err,isfatal,fname):
    if err:
      if isfatal: print '    :: Fatal ERROR : %s' % err
      else:       print '    :: %s' % err
    else:
      print '    :: created file %s' % fname

  date=dateu.fix_date(date)
  title=opt.atts_info(cf)['title']
  flags=opt.flags_info(cf=cf)

  now=time.strftime("%Y-%m-%d %H:%M:%S +0",time.gmtime())
  print '  [%s]' % (now)

  # ----------------------------------------------
  # gen ini:
  # ----------------------------------------------
  print '  GEN ini %s %s' % (date,FA),
  err,isfatal,ini=gen_ini(date,FA='a',cf=cf)
  check_gen(err,isfatal,ini)
  if isfatal: return '',0,err


  # ----------------------------------------------
  # gen blk:
  # ----------------------------------------------
  if flags['atmblk']:
    print '  GEN blk %s %s' % (date,FA),
    err,isfatal,blk=gen_atmfrc(date,FA,cf=cf)
    check_gen(err,isfatal,blk)
    if isfatal: return '',0,err

  # ----------------------------------------------
  # gen tidal frc:
  # ----------------------------------------------
  if flags['tidalfrc']:
    print '  GEN tides %s %s' % (date,FA),
    err,isfatal,tdl=gen_tidalfrc(date,FA,cf=cf)
    check_gen(err,isfatal,tdl)
    if isfatal: return '',0,err

  # ----------------------------------------------
  # gen river frc:
  # ----------------------------------------------
  if flags['riverfrc']:
    print '  GEN rivers %s %s' % (date,FA),
    err,isfatal,riv=gen_rivfrc(date,FA,cf=cf)
    check_gen(err,isfatal,riv)
    if isfatal: return '',0,err

  # ----------------------------------------------
  # gen clm and bry:
  # ----------------------------------------------
  if flags['clmbry']:
    print '  GEN clm bry %s %s' % (date,FA),
    err,isfatal,clm,bry=gen_clmbry(date,FA,cf=cf)
    check_gen(err,isfatal,clm+' '+bry)
    if isfatal: return '',0,err

  # ----------------------------------------------
  # gen roms_in
  # ----------------------------------------------
  print '  GEN .in %s %s' % (date,FA),
  err,isfatal,rin=gen_in(date,FA,cf=cf)
  check_gen(err,isfatal,rin)
  if isfatal: return '',0,err

  # ----------------------------------------------
  # gen queueing sub file
  # ----------------------------------------------
  if flags['qsub']:
    print '  GEN queueing sub file %s %s' % (date,FA),
    err,isfatal,fsub=gen_sub(date,FA,cf=cf)
    check_gen(err,isfatal,fsub)
    if isfatal: return '',0,err


  now=time.strftime("%Y-%m-%d %H:%M:%S +0",time.gmtime())
  if flags['qsub']: s='submitted'
  else: s='started'

  print '  %s %s %s %s              [%s]' % (title,date,FA,s,now)
  # maybe no seed to send emails on every submission...
  #if sendEmail: send_email.send(emailInfo['dest'],sys.stdout.content,s)

  nAttempts=10
  nAt=0
  dtLim=2 # if run took less then dtLim min and was not successful, retry.
  # there is a bug here: job may be waiting more than 5 min in queue !!
  # then if not is_roms_out_ok the oof will stop.
  # The solution is to calc dt as the time since model execution
  ti=time.time()
  dtexc=0
  rout=''
  while not is_roms_out_ok(rout) and nAt<nAttempts and dtexc<dtLim:
    nAt+=1
    print 'Attempt ',nAt

    if flags['qsub']:
      status,rout,dtexc=__run_queue(fsub,date,FA,cf)
      # if forecast and job is in queue for too long (status 9), just dont run it!
      if status==9 and FA=='f': break

    else:
      status,rout,dtexc=__run_local(date,FA,cf)

  runErr=''
  if status!=0:
    print '    :: ERROR ',status
    runErr='status %d'% status
    if os.path.isfile(rout):
      os.rename(rout,rout+'_ERROR')
    else: open(rout+'_ERROR_%d' % status,'w').close()


  return rout,(time.time()-ti)/60.,runErr




