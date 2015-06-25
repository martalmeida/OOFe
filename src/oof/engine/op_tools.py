import time
import os
from string import join as sjoin
import sys
import ConfigParser
import glob
from okean import dateu
from okean.cookbook import relativepath
import shutil
import datetime

CONF='oof.conf'

class Redirect:
  '''class to hold sys.stdout in a string (ex: to send to mail)
  '''
  def __init__(self, s=''):
    self.content = []
    if s: self.write(s)

  def write(self, s): self.content.append(s)
  def flush(self):  self.__init__()


def parse_conf(config_file=CONF):
  '''Reads the configuration file and returns a ConfigParser object
  '''

  config = ConfigParser.ConfigParser()
  if not os.path.isfile(config_file):
    err='config file not found, '+config_file
    return False,err

  config.read(config_file)

  try:
    confType=config.items('CONF')[0][1]
  except:
    err='cannot find type of config file, '+config_file
    return False,err

  return config, ''


def get_conf(config_file,section,option=False,type=eval):
  '''returns conf data
  '''
  out=False
  c,err=parse_conf(config_file)
  if not err:
    try:
      items=dict(c.items(section))
    except ConfigParser.NoSectionError,e:
      err=e

    if not err:
      if option:
        if items.has_key(option):  out=type(items[option])
        else: err='No option: %s' % option
      else:
        if type==str: out=items
        else:
          for k in items.keys(): items[k]=type(items[k])
          out=items

  return out, err


def get_plconf(config_file,section,option=False,type=eval):
  '''get conf data from plots conf file
     checks number of figs to plot and returns conf data for each
     conf data is separated by ; in conf file. If not, same data is
     used in all plots

     ex: for 3 plots,
     data=A;B;C --> A for 1st, B for 2nd, etc
     data=A     --> A for all
     data=A;B   --> A for 1st, B for all others
     data=;B;   --> '' for 1st, B for 2nd and '' for 3rd
  '''

  Out, Err=get_conf(config_file,section,option,type=str)
  if Err: return Out, Err

  # number of figures:
  out, err=get_conf(config_file,'FIGURE','tag',type=str)
  if err: return out, err

  nfigs=len(out.split(';'))
  if option:
    Out=Out.split(';')
    for i in range(nfigs-len(Out)): Out+=[Out[-1]]

    # apply type:
    for i in range(len(Out)):
      try: Out[i]=type(Out[i])
      except: pass

  else:
    for k in Out.keys():
      tmp=Out[k].split(';')
      for i in range(nfigs-len(tmp)): tmp+=[tmp[-1]]
      Out[k]=tmp

      # apply type:
      for i in range(len(Out[k])):
        try: Out[k][i]=type(Out[k][i])
        except: pass
#        if Out[k][i]: Out[k][i]=type(Out[k][i])


  return Out,''


def str_replace(s,old,new):
  '''same as s.replace but replace several items at same time
  replaces the items from the ietrable old by the items from new
  '''
  if isinstance(old,str): old=old,
  if isinstance(new,str): new=new,
  for i in range(len(old)): s=s.replace(old[i],new[i])
  return s


def name_rep(name,**kargs):
  '''replaces in string name the kargs.keys by kargs.values
  '''
  old=['#'+x+'#' for x in kargs.keys()]
  new=kargs.values()
  return str_replace(name,old,new)


def nameof(ioe,type,date='',FA='??',nest=0,cf=CONF,**kargs):
  '''return names with path of roms files, input, output and external
  ioe='in', 'out', 'ext', 'aux'
  '''

  inStoragePath  = kargs.get('istorage',False)
  outStoragePath = kargs.get('ostorage',False)
  extStoragePath = kargs.get('estorage',False)
  auxStoragePath = kargs.get('astorage',False)

  if ioe in ('in',0):
    NAMEsection = 'NAME_INPUTS'
    NAMEoption  = 'name_in_'+type
    PATHoption1 = 'inputs'
    PATHoption2 = 'inputs_'+type
  elif ioe in ('out',1):
    NAMEsection = 'NAME_OUTPUTS'
    NAMEoption  = 'name_out_'+type
    PATHoption1 = 'outputs'
    PATHoption2 = 'outputs_'+type
  elif ioe in ('ext',2):
    NAMEsection = 'NAME_EXTERNAL'
    NAMEoption  = 'name_ext_'+type
    PATHoption1 = 'external'
    PATHoption2 = 'external_'+type
  elif ioe=='aux':
    NAMEsection = 'NAME_AUX'
    NAMEoption  = 'name_aux_'+type
    PATHoption1 = 'aux'
    PATHoption2 = 'aux_'+type


  PATHsection = 'PATHS'
  path0,e=get_conf(cf,PATHsection,'root',type=str)
  if path0=='.': path0=os.path.realpath(os.path.dirname(cf))
  else: path0=os.path.realpath(path0)
  path1,e=get_conf(cf,PATHsection,PATHoption1,type=str)
  path2,e=get_conf(cf,PATHsection,PATHoption2,type=str)

  name,err=get_conf(cf,NAMEsection,NAMEoption,type=str)
  if err:
    print err
    return

  try: year=dateu.parse_date(date).year
  except: year=''

  if isinstance(date,datetime.datetime): date=dateStr=date.strftime('%Y%m%d')
  else: dateStr=date

  name=name_rep(name,DATE=dateStr,NEST=str(nest),FA=FA,YEAR=str(year))

  if inStoragePath and ioe=='in':
    return os.path.join(inStoragePath,name)
  elif outStoragePath and ioe=='out':
    return os.path.join(outStoragePath,name)
  elif extStoragePath and ioe=='ext':
     return os.path.join(extStoragePath,name)
  elif auxStoragePath and ioe=='aux':
     return os.path.join(auxStoragePath,name)
  else:
    return os.path.join(path0,path1,path2,name)


def nameof_run(cf=CONF,FA='a'):
  '''returns roms executable with path
  '''
  roms,e  = get_conf(cf,'NAME_RUN','name_run',type=str)
  path0,e = get_conf(cf,'PATHS','root',type=str)
  if path0=='.': path0=os.path.realpath(os.path.dirname(cf))
  else: path0=os.path.realpath(path0)
  path1,e = get_conf(cf,'PATHS','runpath',type=str)
  roms=name_rep(roms,FA=FA)

  return os.path.join(path0,path1), roms


def nameof_log(date,FA,nest=0,cf=CONF):

  # currently Type is log

  Type='log'

  date=dateu.parse_date(date).strftime('%Y%m%d')

  name,e  = get_conf(cf,'NAME_LOG','name_'+Type,type=str)
  path0,e = get_conf(cf,'PATHS','root',type=str)
  if path0=='.': path0=os.path.realpath(os.path.dirname(cf))
  else: path0=os.path.realpath(path0)
  path1,e = get_conf(cf,'PATHS','logpath',type=str)
  name=name_rep(name,DATE=date,FA=FA,NEST=str(nest))
  return os.path.join(path0,path1,name)

def pathof(cf,type,subtype=False):
  path0,e = get_conf(cf,'PATHS','root',type=str)
  if path0=='.': path0=os.path.realpath(os.path.dirname(cf))
  else: path0=os.path.realpath(path0)
  path1,e=get_conf(cf,'PATHS',type,type=str)
  if subtype:
    path2,e=get_conf(cf,'PATHS',type+'_'+subtype,type=str)
    p=os.path.join(path0,path1,path2)
  else:
    p=os.path.join(path0,path1)

  return p
  

def get_paths(cf=CONF):
  out,e=get_conf(cf,'PATHS',type=str)
  root=out['root']
  if root=='.': root=os.path.realpath(os.path.dirname(cf))
  else: root=os.path.realpath(root)

  folders=[root]
  for k in out.keys():
    if k=='root': continue
    v=out[k]
    if k.find('_')>=0:
      kbase=k.split('_')[0]
      base=out[kbase]
      folders+=[os.path.join(root,base,v)]
    else:
      folders+=[os.path.join(root,v)]

  folders.sort()
  return folders

def mk_paths(cf=CONF,check=False):
  '''
  Create op paths, all but engine and root
  '''
  folders=get_paths(cf)
  for f in folders:
    if not os.path.isdir(f):
      print  '  create %s' % f
      if not check: os.mkdir(f)
    else:
      print 'folder %s exists' % f


def rm_paths(cf=CONF,check=False):
  '''
  Remove op paths, all but engine and root
  '''
  folders=get_paths(cf)
  folders.reverse()
  print  '  keeping root %s' % folders[-1]
  for f in folders[:-1]: # not nclude root (last folder)
    if os.path.isdir(f):
      print  '  remove %s' % f
      if not check: os.rmdir(f)



def check_paths(cf=CONF):
  '''
  Show op paths contents including folders not in conf
  '''
  folders=get_paths(cf)
  root=folders[0]

  # show contents
  unique=[]
  for f in folders:
    if f in unique: continue
    else: unique+=[f]

    if os.path.isdir(f):
      contents=glob.glob(os.path.join(f,'*'))
      nfiles=0
      for c in contents:
        if not os.path.isdir(c): nfiles+=1
      print 'folder %-25s found with %3d files' % (f,nfiles)
    else:
      print 'folder %-25s NOT found' % f

  print '\nfolders not in conf:'

  # show other possible folders:
  contents=glob.glob(os.path.join(root,'*'))
  for c in contents:
    if not os.path.isfile(c) and c not in unique:
      print c

#  for f in unique:
#    print f
#    contents=glob.glob(os.path.join(f,'*'))
#    for c in contents:
#      if not os.path.isfile(c) and c not in unique:
#        print '    '+c

  return unique


def check_names(cf=CONF):
  '''
  Shows in, out, ext and roms names
  '''
  inp,e=get_conf('NAME_INPUTS',  config_file=cf)
  out,e=get_conf('NAME_OUTPUTS', config_file=cf)
  ext,e=get_conf('NAME_EXTERNAL',config_file=cf)
  roms=read_run(cf)

  print '\nas inputs:'
  for k in inp.keys(): print '  %-20s   %s' % (k,inp[k])

  print '\nas outputs:'
  for k in out.keys(): print '  %-20s   %s' % (k,out[k])

  print '\nas external:'
  for k in ext.keys(): print '  %-20s   %s' % (k,ext[k])

  print '\nroms exec:'
  print '  '+roms


def email_info(cf=CONF):
  info,err = get_conf(cf,'EMAIL',type=str)
  if 'send' in info.keys(): info['send']=eval(info['send'])
  if 'dest' in info.keys(): info['dest']=[i.strip() for i in info['dest'].split(',')]
  return info

def atts_info(cf=CONF):
  atts,err = get_conf(cf,'ATTS',type=str)
  return atts

def dates_info(cf=CONF):
  '''
  Configuration start_date and end_date in the form yyyymmdd
  '''
  start_date,e = get_conf(cf,'DATES','start_date',type=str)
  end_date,e   = get_conf(cf,'DATES','end_date',type=str)
  start_date = sjoin(start_date.split('-'),'')
  end_date   = sjoin(end_date.split('-'),'')
  return dateu.parse_date(start_date),dateu.parse_date(end_date)

def flags_info(cf=CONF):
  flags,err = get_conf(cf,'FLAGS')
  #for k in flags.keys(): flags[k]=eval(flags[k])
  return flags

def atm_info(cf):
  info,e=get_conf(cf,'ATM',type=str)
  return info


def run_sub_info(cf,**kargs):
  '''
  all about running with queueing system
  '''

  date = kargs.get('date','')
  fa   = kargs.get('FA','')

  out={}
  out['fa']=fa

  # run command and path:
  epath,exc=nameof_run(cf=cf,FA=fa)

  # names:
  out['sub0']       = nameof('aux','sub0',date=date,FA=fa,cf=cf)
  out['sub']        = nameof('aux','sub',date=date,FA=fa,cf=cf)
  out['indicator']  = nameof('aux','indic',date=date,FA=fa,cf=cf)

  # folders:
  out['sub_dir'] = pathof(cf,'aux','sub')
  out['run_dir'] = epath

  # in/out:
  rin  = nameof('in','rin',date=date,FA=fa,cf=cf)
  rout = nameof('out','rout',date=date,FA=fa,cf=cf)

  Rin  = relativepath(os.path.join(epath,'any'),rin)
  Rout = relativepath(os.path.join(epath,'any'),rout)

  out['run_cmd']=exc+' '+Rin+' > '+Rout
  out['exc']=exc
  out['rin']=rin
  out['rout']=rout

  # other:
  info,e=get_conf(cf,'SUB',type=str)
  if fa:
    for k in info.keys():
      if k.endswith('_a') or k.endswith('_f'):
        if k[-1]==fa: info[k[:-2]]=info[k]
        info.pop(k)

  out.update(info)


  return out

def run_local_info(cf,**kargs):
  '''
  all about running without queueing system
  '''

  date = kargs.get('date','')
  fa   = kargs.get('FA','')

  out={}

  # run command:
  epath,exc  = nameof_run(cf=cf,FA=fa)
  rin  = nameof('in','rin',date=date,FA=fa,cf=cf)
  rout = nameof('out','rout',date=date,FA=fa,cf=cf)

  out['exc']     = exc
  out['run_dir'] = epath
  out['rin']     = relativepath(os.path.join(epath,'any'),rin)
  out['rout']    = relativepath(os.path.join(epath,'any'),rout)

  if len(exc.split())>1: out['exc']=exc.split()

  return out


def n_pred(cf):
    return int(get_conf(cf,'PRED','npred')[0])

def get_clims(date,var,depth,plconf):
  mes=dateu.parse_date(date).month
  mes='%02d' % mes

  sectionNoDepth='CLIM_'+var.upper()
  if not depth is False:
    section = 'CLIM_'+var.upper()+'_'+str(depth)
  else:
    section = sectionNoDepth

  option  = str(mes)
  res,err=get_plconf(plconf,section,option)

  # if error, try to get the sectionNoDepth:
  if isinstance(err,ConfigParser.NoSectionError):
    section=sectionNoDepth
    res,err=get_plconf(plconf,section,option)

  # if error, try the default option:
  if not res:
    res,err=get_plconf(plconf,section,'default')

  return res


def restart_ini(rst,ini,time=0.):
  try:
    shutil.copy2(rst,ini)
    err=False
  except IOError, e:
    err=e.strerror

  if not err:
    # reset time:
    nc=pync(ini,'w')
    nc.var('scrum_time')[:]=time
    nc.close()
