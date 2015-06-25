import glob
import os
import shutil
import sys
from tempfile import mkdtemp
from string import join as sjoin

from okean import dateu, cookbook as cb

import op_tools as opt


def log_name(cf,ccf):
  today=dateu.currday(format='short',sep='')
  logconf,err = opt.get_conf(ccf,'LOG',type=str)
  name   = logconf['logname']
  create = eval(logconf['create'])

  if create:
    p=opt.pathof(cf,'logpath')
    name=name.replace('#TODAY#',today)
    return os.path.join(p,name)
  else:
    return False


def log_init(cf,ccf):
  name=log_name(cf,ccf)
  if name: return open(log_name(cf,ccf),'a')
  else: return sys.stdout


def log_end(logid):
  if not logid is sys.__stdout__ : logid.close()


def list_files(cf,date1,date2,io,type,FA,nest=0,quiet=True):
  files=cb.odict()
  date=date1
  while date<=date2:
    f=opt.nameof(io,type,date,FA,nest,cf)
    if os.path.isfile(f): files[date]=f
    else: files[date]=False

    date=dateu.next_date(date,1)

  if not quiet:
    for d in files.keys():
      if files[d]:
        f=files[d]
        hs=cb.hsize(os.path.getsize(f))
        print d,' ', f, ' ',hs[0],hs[1]
      else:
        print d,' no file'

  return files


def gen_mdates(cf,prev_month=-1):
  start_date,end_date=opt.dates_info(cf)
  y1,m1,d1=dateu.parse_date(start_date)

  y,m,d=dateu.parse_date(dateu.currday())
  y2,m2=dateu.next_month(y,m,n=prev_month)

  dates=dateu.mrange(y1,m1,y2,m2)
  out=[]
  for i in range(len(dates)-1):
    date1=dates[i]
    date2=dateu.next_date(dates[i+1],-1)
    out+=[(date1,date2)]

  return out


def gen_zip(zipfile,fileslist):
  # create tmp folder:
  tmpFolder=mkdtemp()

  inZip=[]
  n=0
  for date in fileslist.keys():
    f=fileslist[date]
    if f:
      n+=1
      if n==1:
        # create tmp folder:
        tmpFolder=mkdtemp()

      fdest=os.path.join(tmpFolder,os.path.basename(f))
      shutil.copy2(f,fdest)
      inZip+=[f]

  if inZip:
    cb.tar_gz_dir(tmpFolder,zipfile,infolder='')
    # remove tmp folder:
    shutil.rmtree(tmpFolder)

  return inZip



def zip_rout(cf,date1,date2,FA,clean=False,quiet=False,label=False,overwrite=False,output=sys.stdout):
  files=list_files(cf,date1,date2,'out','rout',FA);
  p=opt.pathof(cf,'outputs','rout')

  if not label: zipfile='out_%s_%s_%s.tar.gz' % (date1,date2,FA)
  else: zipfile='out_%s_%s.tar.gz' % (label,FA)
  zipfile=os.path.join(p,zipfile)

  if os.path.isfile(zipfile) and not overwrite:
    if not quiet: print >>output,'zip file % s already exist' % zipfile
    return


  # create zip:
  inZip=gen_zip(zipfile,files)

  if not quiet:
    if inZip:
      print >>output,'Created tar.gz %s with contents:' % zipfile
      for i in inZip: print >>output,'  %s' % i
    else:
      print >>output,'No tar.gz created for %s %s %s' % (date1,date2,FA)

  # remove original files:
  if clean:
    for i in inZip:
      if not quiet: print >>output,'removing %s' % i
      os.remove(i)


def zip_out_monthly(cf,ccf):
  '''Compress monthly model stdout files until previous month - minmonths
  See clean.conf
  '''
  quiet=opt.get_conf(ccf,'FLAGS')[0]['quiet']
  conf,err=opt.get_conf(ccf,'OUT')
  if not conf['run']: return

  dates=gen_mdates(cf,prev_month=-conf['minmonths'])

  # start log:
  flog=log_init(cf,ccf)
  if not quiet: print >>flog, 'zip_out_monthly'.upper()+' :'

  for date1,date2 in dates:
    y,m=dateu.parse_date(date1)[:-1]
    month=dateu.month_names(m).lower()
    label='%s_%d' % (month,y)
    for FA in 'fa':
      zip_rout(cf,date1,date2,FA,conf['clean'],quiet,label,output=flog)

  # end log:
  if not quiet: print >>flog, '' # empty line
  log_end(flog)


def zip_plots(cf,year,month,clean=False,quiet=False,overwrite=False,output=sys.stdout):
  pltpath=opt.nameof('out','plots',cf=cf)

  p=os.path.join(pltpath,'%s' % year,'%02d_*' % month)
  folders=glob.glob(p)
  folders.sort()

  monthn=dateu.month_names(month).lower()
  zipfile='plots_%s_%d.tar.gz' % (monthn,year)
  zipfile=os.path.join(pltpath,'%s' % year,zipfile)

  if os.path.isfile(zipfile) and not overwrite:
    if not quiet: print >>output,'zip file % s already exist' % zipfile
    return

  # create zip:
  if folders: cb.tar_gz_dir(folders,zipfile)

  if not quiet:
    if folders:
      print >>output,'Created tar.gz %s with contents:' % zipfile
      for i in folders: print >>output,'  %s' % i
    else:
      print >>output,'No tar.gz created for %d %02d' % (year,month)

  # remove original files:
  if clean:
    for i in folders:
      if not quiet: print >>output,'removing %s' % i
      shutil.rmtree(i)


def zip_plots_monthly(cf,ccf):
  '''Compress monthly model stdout files until previous month - minmonths
  See clean.conf
  '''
  quiet=opt.get_conf(ccf,'FLAGS')[0]['quiet']
  conf,err=opt.get_conf(ccf,'PLOTS')
  if not conf['run']: return

  dates=gen_mdates(cf,prev_month=-conf['minmonths'])

  # start log:
  flog=log_init(cf,ccf)
  if not quiet: print >>flog, 'zip_plots_monthly'.upper()+' :'

  for startMonth,endMonths in dates:
    y,m,d=dateu.parse_date(startMonth)
    zip_plots(cf,y,m,conf['clean'],quiet,overwrite=False,output=flog)

  # end log:
  if not quiet: print >>flog, '' # empty line
  log_end(flog)


def clean_frc(cf,date1,date2,type,FA,nest=0,clean=False,quiet=False,output=sys.stdout):
  date=date1
  while date<=date2:
    f=opt.nameof('in',type,date,FA,nest,cf)
    if os.path.isfile(f):
      if clean:
        if not quiet: print >>output,'Removing ',date,' ', f
        os.remove(f)
    else:
      print >>output,date,' ',FA,' no file',f

    date=dateu.next_date(date,1)


def clean_frc_monthly(cf,ccf):
  '''
  Clean model input atm forcing files until end of n prev months
  Config is done in the configuration file <clean.conf>
  '''

  quiet=opt.get_conf(ccf,'FLAGS')[0]['quiet']

  Types='BLK','FRC'

  # start log:
  flog=log_init(cf,ccf)
  if not quiet: print >>flog, 'clean_frc_monthly'.upper()+' :'

  for Type in Types:
    if not quiet: print >>flog,Type
    conf,err=opt.get_conf(ccf,Type)

    if not conf['run']: continue

    dates=gen_mdates(cf,prev_month=-conf['minmonths'])
    date1=dates[0][0]
    date2=dates[-1][1]
    for FA in ('fa'):
      if FA=='a':
        clean  = conf['aclean']
      elif FA=='f':
        clean  = conf['fclean']

      clean_frc(cf,date1,date2,Type.lower(),FA,nest=0,clean=clean,quiet=quiet,output=flog)

  # end log:
  if not quiet: print >>flog, '' # empty line
  log_end(flog)


def clean_nc_files(cf,date1,date2,type,FA,nest=0,mdkeep=0,wkeep=-1,clean=False,quiet=False,output=sys.stdout):
  '''
  mdkeep: day,month to keep
  ex: mdkeep=1     => keep day 1 of every month
  ex: mdkeep=(1,1) => keep day 1 of January (month,day)
  ex: mdkeep=0     => no keep

  wkeep: day of week to keep:
  ex: wkeep=0  => keep first day of week (synday)
  ex: wkeep=-1 => no keep
  '''


  date=date1
  while date<=date2:
    f=opt.nameof('out',type,date,FA,nest,cf)
    if os.path.isfile(f):
      hs=cb.hsize(os.path.getsize(f))

      y,m,d=dateu.parse_date(date)
      dweek=dateu.parse_date(date).weekday()

      if mdkeep==-1: MDkeep=dateu.mndays(y,m) # last day of month, then calc last day:
      else: MDkeep=mdkeep

      if MDkeep and MDkeep==d or MDkeep==(m,d):
        if not quiet: print >>output,'*Keeping ',date,' ', f, ' ',hs[0],hs[1],'**', MDkeep
      elif wkeep!=-1 and wkeep==dweek:
        if not quiet: print >>output,'*Keeping ',date,' ', f, ' ',hs[0],hs[1],'*', wkeep
      else:
        if not quiet:
          if clean: print >>output,'Removing ',date,' ', f, ' ',hs[0],hs[1]
          else:     print >>output,'Not removing ',date,' ', f, ' ',hs[0],hs[1]

        if clean: os.remove(f)
    else:
      print >>output,date,' ',FA,' no file'

    date=dateu.next_date(date,1)


def clean_nc_files_monthly(cf,ccf):
  '''
  Clean model output NetCDF files until end of n prev months
  Config is done in the configuration file <clean.conf>
  '''

  quiet=opt.get_conf(ccf,'FLAGS')[0]['quiet']

  Types='HIS','AVG','RST','FLT'

  # start log:
  flog=log_init(cf,ccf)
  if not quiet: print >>flog, 'clean_nc_files_monthly'.upper()+' :'

  for Type in Types:
    if not quiet: print >>flog,Type
    conf,err=opt.get_conf(ccf,Type)

    if not conf['run']: continue

    dates=gen_mdates(cf,prev_month=-conf['minmonths'])
    date1=dates[0][0]
    date2=dates[-1][1]
    for FA in ('fa'):
      if FA=='a':
        clean  = conf['aclean']
        mdkeep = conf['amdkeep']
        wkeep  = conf['awkeep']
      elif FA=='f':
        clean  = conf['fclean']
        mdkeep = conf['fmdkeep']
        wkeep  = conf['fwkeep']

      clean_nc_files(cf,date1,date2,Type.lower(),FA,nest=0,mdkeep=mdkeep,wkeep=wkeep,clean=clean,quiet=quiet,output=flog)

  # end log:
  if not quiet: print >>flog, '' # empty line
  log_end(flog)


def clean_ini(cf,date1,date2,FA='a',nest=0,clean=False,quiet=False,output=sys.stdout):
  '''Create text file with the current ini links
  If the ini file is a link is can be unlinked; if it is a file it
  is not removed !
  '''
  def read_log(f):
    out=cb.odict()
    if os.path.isfile(f):
      L=open(log).readlines()
      for l in L:
        tmp=l.split(' ',1)
        sdate=tmp[0]
        scontents=tmp[1].rstrip().split(' + ')
        out[tmp[0]]=scontents

    return out

  def gen_log(f,L):
    i=open(f,'w')
    keys=L.keys()
    keys.sort()
    for d in keys:
      scontents=sjoin(L[d],' + ')
      i.write('%s %s\n' % (d,scontents))

    i.close()

  def add2log(f,add):
    L=read_log(f)
    L0=L.copy()
    sdate=add[0]
    contents=add[1].rstrip()
    if L.has_key(sdate) and contents not in L[sdate]:
      L[sdate]+=[contents]
      #if not quiet: print >>output,' +'+sdate+' '+contents
    elif not L.has_key(sdate):
      L[sdate]=[contents]
      #if not quiet: print >>output,'  '+sdate+' '+contents

    if L!=L0:
      gen_log(f,L)
      return True
    else: return False # file has not changed

  files=[]
  date=date1

  log='ini_log_%s_%s.txt' % (date1,date2)
  p=opt.pathof(cf,'inputs','ini')
  log=os.path.join(p,log)

  if not quiet: print >>output,'Creating/updating ini log %s' % log

  HasChanged=False
  while date<=date2:
    f=opt.nameof('in','ini',date,FA,nest,cf)
    if os.path.islink(f):
      src=os.readlink(f)
      add=(date,'%s --> %s' % (f,src))
      hasChanged=add2log(log,add)
      HasChanged=HasChanged or hasChanged
      if clean:
        # remove link:
        if not quiet: print >>output,'removing %s' % f
        os.remove(f)

    elif os.path.isfile(f):
      hs=cb.hsize(os.path.getsize(f))
      ssize='%s %s' % (str(hs[0]),hs[1])
      add=(date,'%s --> %s' % (f,ssize))
      hasChanged=add2log(log,add)
      HasChanged=HasChanged or hasChanged
      if not quiet:  print >>output,date,' keeping ', f, ' ',hs[0],hs[1]
    else:
      print >>output,date,' no file'

    date=dateu.next_date(date,1)

  if not quiet:
    if HasChanged:  print >>output,'  file has changed'
    else:           print >>output,'  file has not changed'


def clean_ini_monthly(cf,ccf):
  '''
  Clean model ini link files until end of n prev months
  Config is done in the configuration file <clean.conf>

  Create text file with the current ini links
  If the ini file is a link is can be unlinked; if it is a file it
  is not removed !
  '''
  quiet=opt.get_conf(ccf,'FLAGS')[0]['quiet']
  conf,err=opt.get_conf(ccf,'INI')
  clean=conf['clean']

  if not conf['run']: return

  # start log:
  flog=log_init(cf,ccf)
  if not quiet: print >>flog, 'clean_ini_monthly'.upper()+' :'

  dates=gen_mdates(cf,prev_month=-conf['minmonths'])
  for startMonth,endMonth in dates:
    clean_ini(cf,startMonth,endMonth,FA='a',nest=0,clean=clean,quiet=quiet,output=flog)

  # end log:
  if not quiet: print >>flog, '' # empty line
  log_end(flog)


if __name__=='__main__':

  if len(sys.argv)==4:
    cf   = sys.argv[1]
    ccf  = sys.argv[2]
    task = sys.argv[3]
  else:
    task = sys.argv[1]
    thisDir=os.path.dirname(sys.argv[0])
    prevDir=os.path.realpath(os.path.join(thisDir,'..'))
    cf  = os.path.join(prevDir,'oof.conf')
    ccf = os.path.join(prevDir,'clean.conf')

  if task in ('zip_out','all'):     zip_out_monthly(cf,ccf)
  if task in ('zip_plots','all'):   zip_plots_monthly(cf,ccf)
  if task in ('clean_nc','all'):    clean_nc_files_monthly(cf,ccf)
  if task in ('clean_ini','all'):   clean_ini_monthly(cf,ccf)
  if task in ('clean_frc','all'):   clean_frc_monthly(cf,ccf)

