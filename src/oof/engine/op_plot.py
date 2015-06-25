import os
import datetime
from glob import glob
import numpy as np
import pylab as pl
from mpl_toolkits.basemap import Basemap

from okean import dateu, pl_plots, roms, netcdf

import op_tools as opt


def plt_grid(cf,grd,ifig=0):
  '''
  Plot grid
  '''

  if isinstance(grd,basestring): grd=roms.Grid(grd)

  # start figure
  figConf,err=opt.get_plconf(cf,'FIGURE')
  fig_size     = figConf['size'][ifig]
  fig_bgcolor  = figConf['bgcolor'][ifig]
  fig_fontsize = figConf['def_fontsize'][ifig]
  fig_linewidth= figConf['def_linewidth'][ifig]

  fig=pl.figure(figsize=fig_size,facecolor=fig_bgcolor)
  pl.matplotlib.rcParams['font.size']=fig_fontsize
  pl.matplotlib.rcParams['lines.linewidth']=fig_linewidth

  # grid data:
  grdConf,err=opt.get_plconf(cf,'GRID')
  lonlims    = grdConf['lonlims'][ifig]
  latlims    = grdConf['latlims'][ifig]
  proj       = grdConf['proj'][ifig]
  resolution = grdConf['resolution'][ifig]

  # start projection:
  if lonlims=='auto': lonlims=grd.lon.min(),grd.lon.max()
  if latlims=='auto': latlims=grd.lat.min(),grd.lat.max()
  if proj=='merc':
    m = Basemap(projection=proj,
              resolution=resolution,
              urcrnrlon=lonlims[1], urcrnrlat=latlims[1],
              llcrnrlon=lonlims[0], llcrnrlat=latlims[0])
  else:
    pass # TODO

  # add axes:
  axData,err=opt.get_plconf(cf,'AXES')
  axpos = axData['position'][ifig]
  axbg  = axData['bgcolor'][ifig]
  ax = fig.add_axes(axpos,axisbg=axbg)

  # bathy contour and border:
  h=np.ma.masked_where(grd.mask==0,grd.h)
  xb,yb=grd.border()
  x, y = m(grd.lon, grd.lat)
  xb, yb = m(xb,yb)

  Data,err = opt.get_plconf(cf,'BATHY')
  add   = Data['add'][ifig]
  color = Data['color'][ifig]
  width = Data['width'][ifig]
  levels= Data['levels'][ifig]
  if add: ax.contour(x, y, h, levels,colors=color,linewidths=width)
  ax.plot(xb,yb,linewidth=width,color=color)
  ax.axis([m.xmin, m.xmax, m.ymin, m.ymax])

  # coastlines:
  clData,err = opt.get_plconf(cf,'COAST')
  add   = clData['add'][ifig]
  color = clData['color'][ifig]
  width = clData['width'][ifig]
  if add: m.drawcoastlines(linewidth=width,color=color)

  # land:
  Data,err = opt.get_plconf(cf,'LAND')
  add   = Data['add'][ifig]
  color = Data['color'][ifig]
  if add: m.fillcontinents(color=color)

  # countries:
  Data,err = opt.get_plconf(cf,'COUNTRIES')
  add   = Data['add'][ifig]
  color = Data['color'][ifig]
  width = Data['width'][ifig]
  if add: m.drawcountries(linewidth=width,color=color)

  # states:
  Data,err = opt.get_plconf(cf,'STATES')
  add   = Data['add'][ifig]
  color = Data['color'][ifig]
  width = Data['width'][ifig]
  if add: m.drawstates(linewidth=width,color=color)


  # rivers:
  Data,err = opt.get_plconf(cf,'RIVERS')
  add   = Data['add'][ifig]
  color = Data['color'][ifig]
  width = Data['width'][ifig]
  if add: m.drawrivers(linewidth=width,color=color)


  # paralels:
  Data,err = opt.get_plconf(cf,'PARALELS')
  add   = Data['add'][ifig]
  color = Data['color'][ifig]
  width = Data['width'][ifig]
  ticks = Data['ticks'][ifig]
  dashes= Data['dashes'][ifig]
  if add: m.drawparallels(ticks, labels=[1,0,0,0],dashes=dashes,linewidth=width,color=color)

  # meridians:
  Data,err = opt.get_plconf(cf,'MERIDIANS')
  add   = Data['add'][ifig]
  color = Data['color'][ifig]
  width = Data['width'][ifig]
  ticks = Data['ticks'][ifig]
  dashes= Data['dashes'][ifig]
  if add: m.drawmeridians(ticks, labels=[0,0,0,1],dashes=dashes,linewidth=width,color=color)

  return m,fig,ax


def plt0(cf,pcf):
  title=opt.atts_info(cf)['title']
  '''
  Plot grids
  '''

  pltpath=opt.nameof('out','plots',cf=cf)
  grd = glob(opt.nameof('in','grd',cf=cf))[0]

  if not os.path.isfile(grd):
    print ':: grid file not found'
    return

  # figure tags:
  out, err=opt.get_plconf(pcf,'FIGURE','tag')
  for i in range(len(out)):
    m,fig,ax=plt_grid(pcf,grd,ifig=i)
    savename='plt0'
    if out[i]: savename=savename+'_%s' % (out[i])
    savename=os.path.join(pltpath,savename+'.png')

    pl.savefig(savename,dpi=pl.gcf().dpi)
    print 'saving %s' % savename


def plt_hslice(conf,plconf,date,FA='a',nest=0,**kargs):
  err=''
  fig=False
  info={}

  type     = 'avg'
  var      = 'temp'
  slice    = 'z'
  ind      = -10
  time     = -1
  currents = False
  dcurr    = (3,3)
  scurr    = 3
  lcurr    = 0.2
  ifig     = 0
# closefig = True
  clim     = False
  quiet    = False
  outStoragePath=False
  cmap     = None
  norm     = None
  useBar   = True # currents are barotropic for 2D vars (like zeta)

  keys=kargs.keys()
  if 'type'     in keys: type     = kargs['type']
  if 'var'      in keys: var      = kargs['var']
  if 'slice'    in keys: slice    = kargs['slice']
  if 'ind'      in keys: ind      = kargs['ind']
  if 'time'     in keys: time     = kargs['time']
  if 'currents' in keys: currents = kargs['currents']
  if 'dcurr'    in keys: dcurr    = kargs['dcurr']
  if 'scurr'    in keys: scurr    = kargs['scurr']
  if 'lcurr'    in keys: lcurr    = kargs['lcurr']
  if 'ifig'     in keys: ifig     = kargs['ifig']
  if 'closefig' in keys: closefig = kargs['closefig']
  if 'clim'     in keys: clim     = kargs['clim']
  if 'quiet'    in keys: quiet    = kargs['quiet']
  if 'ostorage' in keys: outStoragePath = kargs['ostorage']
  if 'cmap'     in keys: cmap     = kargs['cmap']
  if 'usebar'   in keys: useBar   = kargs['usebar']
  if 'norm'     in keys: norm     = kargs['norm']

  date=dateu.parse_date(date)

  # find input files:
  args={'cf':conf,'date':date,'FA':FA,'nest':nest,'ostorage':outStoragePath}
  his = opt.nameof('out',type,**args)
  clm = opt.nameof('in','clm',**args)
  grd = opt.nameof('in','grd',**args)
  if not os.path.isfile(his):
    err='Main file not found (%s)' % his
    return err,fig,info
  if not os.path.isfile(grd):
    err='Grid file not found (%s)' % grd
    return err,fig,info
  r=roms.His(his,grd)

  # plot grid:
  proj,fig, ax = plt_grid(plconf,grd,ifig)

  def add_colorbar(handle,**args):
    ax=pl.gca()
    Data,err = opt.get_plconf(plconf,'AXES')
    cbpos    = Data['cbpos'][ifig]
    cbbgpos  = Data['cbbgpos'][ifig]
    cbbgc    = Data['cbbgcolor'][ifig]
    cbbga    = Data['cbbgalpha'][ifig]
    cblab    = Data['cblabel'][ifig]

    # colorbar bg axes:
    if cbbgpos:
      rec=pl.axes((cbpos[0]-cbpos[2]*cbbgpos[0],cbpos[1]-cbbgpos[2]*cbpos[3],
                      cbpos[2]*(1+cbbgpos[0]+cbbgpos[1]),cbpos[3]*(1+cbbgpos[2]+cbbgpos[3])),
                      axisbg=cbbgc,frameon=1)

      rec.patch.set_alpha(cbbga)
      rec.set_xticks([])
      rec.set_yticks([])
      for k in rec.axes.spines.keys():
        rec.axes.spines[k].set_color(cbbgc)
        rec.axes.spines[k].set_alpha(cbbga)


    # colorbar:
    if cbpos:
      cbax=fig.add_axes(cbpos)
      if cbpos[2]>cbpos[3]: orient='horizontal'
      else: orient='vertical'
      cb=pl.colorbar(handle,cax=cbax,orientation=orient,drawedges=0,**args)
      pl.axes(ax)

    # colorbar label:
    if cblab:
      Data,err = opt.get_plconf(plconf,'HSLICES')
      varnames=Data['varnames'][ifig].split(',')
      vnames=Data['vnames'][ifig].split(',')
      lab=''
      for i in range(len(varnames)):
        if varnames[i].strip()==var:
          lab=vnames[i].strip()
          break

      if lab:
        if r.hasz(var):
          if slice=='k':
            if ind==0: lab = 'Bottom '+lab
            elif ind in (-1,'surface'): lab = 'Surface '+lab
          elif slice=='z':
            lab=lab+' '+str(ind)+'m'

        cb.set_label(lab)


  def add_currkey(handle):
    Data,err = opt.get_plconf(plconf,'HSLICES')
    pos=Data['kcurrpos'][ifig]
    if pos:
      pl.quiverkey(handle, pos[0], pos[1], lcurr, '%s m/s' % str(lcurr),labelpos='S',
                                              coordinates='axes')

  # hslice:
  if var:
    if   slice=='k': metodo=r.slicek
    elif slice=='z': metodo=r.slicez

    x,y,z,v=metodo(var,ind,time,plot=False)
    x,y=proj(x,y)

    # cmap:
    if isinstance(cmap,basestring):
      try:cmap=pl.cm.cmap_d[cmap]
      except:
        try:
          from okean import pl_tools
          cmap=pl_tools.cm.cmap_d[cmap]
        except: cmap=pl.cm.jet

    # original data from clm
    if slice=='k' and ind in (-1,) and var+'_original' in netcdf.varnames(clm):
      tcurr= r.datetime[time]
      x_o=netcdf.use(clm,'x_original')
      y_o=netcdf.use(clm,'y_original')
      x_o,y_o=proj(x_o,y_o)
      v_o=netcdf.use(clm,'y_original')
      t_o=netcdf.nctime(clm,'clim_time')

      # average to current time:
      i0,=np.where(t_o<=tcurr)[-1]
      i1,=np.where(t_o>tcurr)[0]
      v_o0=netcdf.use(clm,var+'_original',time=i0)
      v_o1=netcdf.use(clm,var+'_original',time=i1)
      # avg:
      a=tcurr-t_o[i0]
      b=t_o[i1]-tcurr

      a=a.days*86400+a.seconds
      b=b.days*86400+b.seconds

      if a==0: v_o=v_o0
      elif b==0: v_o=v_o1
      else: v_o=(v_o0*b+v_o1*a)/(a+b)

      pch=pl.pcolormesh(x_o,y_o,v_o,shading='flat',cmap=cmap)
      if clim: pl.clim(clim[0],clim[1])

    if norm=='log':
      from matplotlib.colors import LogNorm
      Norm=LogNorm(vmin=clim[0],vmax=clim[1])
    else: Norm=None

    # change hypoxia colorbar/cmap
    if var=='dye_01':
      HypoxiaLim=135
      from okean import pl_tools
      cmap=pl_tools.ucmaps().gen_oxygen(v=(0,HypoxiaLim,300.)) # default is 0,135,300 !!

    pch=pl.pcolormesh(x,y,v,shading='flat',cmap=cmap, norm=Norm)
    if clim: pl.clim(clim[0],clim[1])

    # hypoxia:
    if var=='dye_01' and ind==0 and ifig==0:
      cond=v<135.
      cond=v<HypoxiaLim
      cond=(v<HypoxiaLim)&(r.grid.h>5)

      pm=r.grid.use('pm')
      pn=r.grid.use('pn')
      A=(1/pm[cond]*1/pn[cond]/1e6).sum()

      x_,y_=proj(-98,29.5)
      pl.text(x_,y_,'Hypoxia area = %.0f km$^2$' % A,color='r',
                       fontweight='bold',fontname='monospace',
                       bbox=dict(edgecolor='none',facecolor='white', alpha=0.8))
    # hypoxia.

    # colorbar:
    if norm=='log':
      tks=10**np.linspace(np.log10(clim[0]),np.log10(clim[1]),4)
      opts={'ticks':tks,'format':'%.2f'}
    else: opts={'ticks':None}
    add_colorbar(pch,**opts)

  if currents:
    if (var and r.hasz(var)) or not useBar:  uvind=ind
    else: uvind='bar'

    x,y,z,u,v=r.sliceuv(uvind,time)
    xm, ym = proj(x,y)
    mm=np.zeros(x.shape,'bool')
    mm[::dcurr[0],::dcurr[1]]=True


    Data,err = opt.get_plconf(plconf,'HSLICES')
    wcurr=Data['wcurr'][ifig]
    acurr=Data['acurr'][ifig]

    qvopts={'units':'x','scale':scurr,'width':wcurr,'alpha':acurr}
    if var:
      q=pl.quiver(xm[mm],ym[mm],u[mm],v[mm],**qvopts)
    else:
      s=np.sqrt(u**2+v**2)
      q=pl.quiver(xm[mm],ym[mm],u[mm],v[mm],s[mm],**qvopts)
      if clim: pl.clim(clim[0],clim[1])
      add_colorbar(q)

    add_currkey(q)

  # store some info that may be required later
  info['hasz']=False
  if var and r.hasz(var): info['hasz']=True


  # logo:
  if ifig==0:
    im=os.path.join(os.path.dirname(__file__),'logo_INOCAR.png')
    i=pl.imread(im)
    h,w=i.shape[:2]
    rx=.12
    W=(proj.xmax- proj.xmin)*rx
    H=W*h/w
    l=proj.xmax
    #pl.fill([proj.xmax-W, proj.xmax, proj.xmax,     proj.xmax-W],
    #           [proj.ymin,   proj.ymin, proj.ymin+2.8*H, proj.ymin+2.8*H],
    #           '#500000',alpha=0.25,ec='none')

    ax.imshow(i,extent=(proj.xmax*.98-W,proj.xmax*.98, proj.ymin+H*.1, proj.ymin+H*1.1),zorder=1e3)
    #pl.text(proj.xmax-W/2., proj.ymin+2.2*H,'OOF',
    #           fontdict={'size':14,'family':'serif'},
    #           color='#500000',ha='center',weight='bold')

    pl.text(proj.xmax*.8, proj.ymax*(-.1),r.datetime[time].strftime("%d %b %Y"),
               fontdict={'size':11,'family':'monospace'},ha='center')

    if FA=='f':
      s='Pronostico desde %s' % r.datetime[0].strftime("%d %b %Y")
      pl.text(proj.xmax*.8, proj.ymax*(-.15),s,
      #pl.text(proj.xmax-W/2., proj.ymin+1.1*H,s,
                 fontdict={'fontsize':10},ha='center')
  # logo.

  # lims change in some mpl versions !!
  pl.gca().axis([proj.xmin, proj.xmax, proj.ymin, proj.ymax])

  return err, fig, info


def op_plt_hslice(conf,plconf,date,FA,nest=0,**kargs):
  closefig = kargs.get('closefig',True)
  clearfig = kargs.get('clearfig',True)
  save     = kargs.get('save',True)
  Varname  = kargs.get('vname',False)
  Depth    = kargs.get('depth',False)

  date=dateu.parse_date(date)

  Err=[]
  Out=[]
  pltpath = opt.nameof('out','plots',cf=conf)

  Figure,err  = opt.get_plconf(plconf,'FIGURE')
  Hslices,err = opt.get_plconf(plconf,'HSLICES')
  Title,err=opt.get_plconf(plconf,'AXES','title')

  def iterv(v):
    try: len(v)
    except: v=[v]
    return v

  for i in range(len(Figure.values()[0])):  # loop figures
    Varnames = Hslices['varnames'][i].split(',')
    Varnames=[s.strip() for s in Varnames]

    depths   = Hslices['depths'][i]
    addcurr  = Hslices['addcurr'][i]
#    clims    = Hslices['clim'][i]

    depths  = iterv(depths)
    addcurr = iterv(addcurr)
#    clims   = iterv(clims)

    kargs={}
    kargs['ifig']=i
    kargs['type']=Hslices['input'][i]
    #kargs['time']=Inputs['time'][i]
    TIMES=Hslices['time'][i]

    kargs['dcurr']=Hslices['dcurr'][i]
    kargs['scurr']=Hslices['scurr'][i]
    kargs['lcurr']=Hslices['lcurr'][i]

    if Varname: varnames=[Varname]
    else: varnames=Varnames

    for var in varnames: # loop variables
      var=var.strip()

      nv=Varnames.index(var)
      kargs['cmap']=Hslices['cmap'][i].split(',')[nv].strip()
      kargs['norm']=Hslices['norm'][i].split(',')[nv].strip()

      kargs['var']=var
      vdepths=depths[nv]

      try: iter(vdepths)
      except: vdepths=[vdepths]

      if Depth: vdepths=[Depth]

      nz=-1
      for z in vdepths: # loop depths
        nz+=1
        if z in ('s','surf','surface') or z>=0:
          kargs['ind']   = z
          kargs['slice'] = 'k'
        else:
          kargs['ind']   = z
          kargs['slice'] = 'z'


        cl=opt.get_clims(date,var,z,plconf)[i]

        kargs['clim']=cl

        for addc in addcurr: # add/no currents
          kargs['currents']   = addc



          # loop over time:
          if TIMES=='all':
            if FA=='a': times=[-1]
            else: times=range(int(opt.get_conf(conf,'PRED','npred')[0]))
          else: times=[TIMES]


          for it in times:
            kargs['time']=it

            e,fig,info=plt_hslice(conf,plconf,date,FA,nest,**kargs)
            Err+=[e]

            if not e:
              if var: svar=var
              else: svar=''

              if addc: scurr='curr'
              else: scurr=''

              if info['hasz']: sslice=kargs['slice']+'_'+str(kargs['ind'])
              else: sslice=''

              if date.hour>0:
                sdate=date.strftime('%Y%m%d_%H')
              else:
                sdate=date.strftime('%Y%m%d')

              savename='%s_%s_n%d_%s_%d_%s_%s_%s_%s' % (sdate,FA,nest,kargs['type'],kargs['time'],svar,scurr,sslice,Figure['tag'][i])

              if Title[i]:
                simpleTitle=1

                rdate=date.strftime('%d-%m-%Y')

                if sslice: sslice=sslice[2:]
                title='%s#%s#n%d#%s#%d#%s#%s#%s' % (rdate,FA,nest,kargs['type'],kargs['time'],svar,scurr,sslice)

                if simpleTitle: # simpler version of title:
                  if FA=='f': # forecast date:
                    rdate=dateu.next_date(date,kargs['time'])
                    rdate=date.strftime('%d-%m-%Y')


                  title = '%s#%s#%s#%s' % (rdate,svar,scurr,sslice)
                  if FA=='f': title=title+' (forec)'
                
                while 1:
                  if title.find('##')>-1: title=title.replace('##','#')
                  else: break
                title=title.replace('#',' ')
                pl.title(title)



              while 1:
                if savename.find('__')>-1: savename=savename.replace('__','_')
                else: break

              savename=savename.strip('_')

              if save:
                Y,M,D=date.year,date.month,date.day,
                Ydest  = os.path.join(pltpath,'%s' % Y )
                if not os.path.isdir(Ydest): os.mkdir(Ydest)
                MDdest = os.path.join(Ydest,'%02d_%02d' % (M,D) )
                if not os.path.isdir(MDdest): os.mkdir(MDdest)

                savename=os.path.join(MDdest,savename+'.'+Figure['extension'][i])
                Out+=[savename]

                pl.savefig(savename,dpi=pl.gcf().dpi)
                #pl.savefig(savename,dpi=300)

              if clearfig: fig.clear()
              if closefig: pl.close(fig)

  return Err,Out


def plt_flt(conf,plconf,date,FA='f',nest=0,**kargs):
  err  = ''
  fig  = False
  info = ''

  ifig  = kargs.get('ifig',0)
  quiet = kargs.get('quiet',0)

  date=dateu.parse_date(date)

  # find input files:
  args={'cf':conf,'date':date,'FA':FA,'nest':nest}
  flt = opt.nameof('out','flt',**args)
  grd = opt.nameof('in','grd',**args)
  if not os.path.isfile(flt):
    err='FLT file not found (%s)' % flt
    return err,fig,info
  if not os.path.isfile(grd):
    err='Grid file not found (%s)' % grd
    return err,fig,info

  date=dateu.parse_date(date)

  # plot grid:
  proj,fig = plt_grid(plconf,grd,ifig)

  Data,err = opt.get_plconf(plconf,'FLOATS')
  color  = Data['color'][ifig]
  width  = Data['width'][ifig]
  marker  = Data['marker'][ifig]
  mfcolor = Data['markerFaceColor'.lower()][ifig]
  mecolor = Data['markerEdgeColor'.lower()][ifig]
  mewidth = Data['markerEdgeWidth'.lower()][ifig]
  msize   = Data['markerSize'.lower()][ifig]

  f=roms.Flt(flt,grd)
  ntimes,npos=f.lon.shape
  x,y=f.lon[...],f.lat[...]
  x=np.ma.masked_where(x>1e3,x)
  x,y=proj(x,y)

  # initial locations:
  pl.plot(x[0,:],y[0,:],linewidth=0,marker=marker,mec=mecolor,mfc=mfcolor,ms=msize, mew=mewidth)

  # all trajectories:
  for i in range(npos):
    pl.plot(x[:,i],y[:,i],linewidth=width,color=color)


  # tilte:
  Title=opt.get_plconf(plconf,'AXES','title')
  if Title[ifig]:
    simpleTitle=1

    rdate=date.strftime('%d-%m-%Y')

    Ndays=f.tdays[-1]-f.tdays[0]

    title='drifters %s after %s (%4.2f days)' % (FA,rdate,Ndays)
    if simpleTitle:
      title='drifters after %s (%4.2f days)' % (rdate,Ndays)

    pl.title(title)

  # lims change in some mpl versions !!
  pl.gca().axis([proj.xmin, proj.xmax, proj.ymin, proj.ymax])

  return err,fig,info


def op_plt_flt(conf,plconf,date,FA='f',nest=0,**kargs):
  closefig = kargs.get('closefig',True)
  clearfig = kargs.get('clearfig',True)
  save     = kargs.get('save',True)

  date=dateu.parse_date(date)

  Figure,err  = opt.get_plconf(plconf,'FIGURE')

  Err=[]
  Out=[]
  pltpath = opt.nameof('out','plots',cf=conf)

  ifig=-1
  for tag in Figure['tag']:
    ifig+=1

    args={}
    args['ifig']=ifig

    err,fig,info=plt_flt(conf,plconf,date,FA,nest,**args)

    Err+=[err]

    if not err:

      # save:
      if save:
        if tag: Tag='_'+tag
        else: Tag=tag
        savename='floats_%s_%s_n%d%s' % (date,FA,nest,Tag)

        Y,M,D=date.year,date.month,date.day,
        Ydest  = os.path.join(pltpath,'%s' % Y )
        if not os.path.isdir(Ydest): os.mkdir(Ydest)
        MDdest = os.path.join(Ydest,'%02d_%02d' % (M,D) )
        if not os.path.isdir(MDdest): os.mkdir(MDdest)

        savename=os.path.join(MDdest,savename+'.'+Figure['extension'][ifig])
        Out+=[savename]

        pl.savefig(savename,dpi=pl.gcf().dpi)

      if clearfig: fig.clear()
      if closefig: pl.close(fig)

  return Err,Out


def plt_wind(conf,plconf,date,FA='a',nest=0,**kargs):
  err  = ''
  fig  = False
  info = ''

  ifig  = kargs.get('ifig',0)
  day   = kargs.get('day',0)
  quiet = kargs.get('quiet',0)

  time=day
  date=dateu.parse_date(date)

  # find input files:
  args={'cf':conf,'date':date,'FA':FA,'nest':nest}
  atm = opt.nameof('in','blk',**args)
  grd = opt.nameof('in','grd',**args)
  if not os.path.isfile(atm):
    err='ATM file not found (%s)' % atm
    return err,fig,info
  if not os.path.isfile(grd):
    err='Grid file not found (%s)' % grd
    return err,fig,info

  Data,err = opt.get_plconf(plconf,'WIND')
  dcurr=Data['dcurr'][ifig]
  lcurr=Data['lcurr'][ifig]
  scurr=Data['scurr'][ifig]
  clim =Data['clim'][ifig]
  tind = Data['time'][ifig]

  x=netcdf.use(grd,'lon_rho')
  y=netcdf.use(grd,'lat_rho')
  wtime=netcdf.nctime(atm,'time')
  cnd=(wtime>=date+datetime.timedelta(days=day))&(date<date+datetime.timedelta(days=day+1))
  u=netcdf.use(atm,'Uwind',time=cnd)
  v=netcdf.use(atm,'Uwind',time=cnd)
  if tind=='dailyMean':
    u=u.mean(0)
    v=v.mean(0)
    sdate=wtime[cnd][0] # for title... 1st day 00h is expected to be 1st date,
                        # or model should not run!
  else: # tind of some day, ex: tind 0 from forec day 3
    u=u[tind]
    v=v[tind]
    sdate=wtime[cnd][tind]


  if day>len(u)-1:
    err='Invalid day %d (max=%d)' % (day,len(u)-1)
    return err,fig,info

  # plot grid:
  proj,fig,ax= plt_grid(plconf,grd,ifig)


  # no mask on land:
  mask=np.zeros(u.shape,'bool')
  mask[::dcurr[0],::dcurr[1]]=True
  xm, ym = proj(x,y)

  s=np.sqrt(u**2+v**2)
  q=pl.quiver(xm[mask],ym[mask],u[mask],v[mask],s[mask],scale=scurr,zorder=100)

  pl.clim(clim[0],clim[1])


  def add_colorbar(handle,**args):
    ax=pl.gca()
    Data,err = opt.get_plconf(plconf,'AXES')
    cbpos    = Data['cbpos'][ifig]
    cbbgpos  = Data['cbbgpos'][ifig]
    cbbgc    = Data['cbbgcolor'][ifig]
    cbbga    = Data['cbbgalpha'][ifig]
    cblab    = Data['cblabel'][ifig]

    # colorbar bg axes:
    if cbbgpos:
      rec=pl.axes((cbpos[0]-cbpos[2]*cbbgpos[0],cbpos[1]-cbbgpos[2]*cbpos[3],
                      cbpos[2]*(1+cbbgpos[0]+cbbgpos[1]),cbpos[3]*(1+cbbgpos[2]+cbbgpos[3])),
                      axisbg=cbbgc,frameon=1)

      rec.patch.set_alpha(cbbga)
      rec.set_xticks([])
      rec.set_yticks([])
      for k in rec.axes.spines.keys():
        rec.axes.spines[k].set_color(cbbgc)
        rec.axes.spines[k].set_alpha(cbbga)


    # colorbar:
    if cbpos:
      cbax=fig.add_axes(cbpos)
      if cbpos[2]>cbpos[3]: orient='horizontal'
      else: orient='vertical'
      cb=pl.colorbar(handle,cax=cbax,orientation=orient,drawedges=0,**args)
      pl.axes(ax)

      # colorbar label:
      cb.set_label(r'Wind Speed [m s$^{\rm{-1}}$]')

  def add_currkey(handle):
    pos=Data['kcurrpos'][ifig]
    if pos:
      pl.quiverkey(handle, pos[0], pos[1], lcurr, '%s m/s' % str(lcurr),labelpos='S',
                                                coordinates='axes')


  add_colorbar(q)
  add_currkey(q)

  # tilte:
  Title,err=opt.get_plconf(plconf,'AXES','title')
  if Title[ifig]:
    simpleTitle=1

    rdate=date.strftime('%d-%m-%Y')
    title='wind %s %s %d' % (rdate,FA,day)


    if simpleTitle: # simpler version of title:
      if FA=='f': # forecast date:
        rdate=dateu.next_date(date,day);
        rdate=rdate.strftime('%d-%m-%Y')

      title='wind %s' % (rdate)
      if FA=='f':
        title=title+' (forec)'

    pl.title(title)


  # logo:
  if ifig==0:
    im=os.path.join(os.path.dirname(__file__),'logo_INOCAR.png')
    i=pl.imread(im)
    h,w=i.shape[:2]
    rx=.12
    W=(proj.xmax- proj.xmin)*rx
    H=W*h/w
    l=proj.xmax
    #pl.fill([proj.xmax-W, proj.xmax, proj.xmax,     proj.xmax-W],
    #           [proj.ymin,   proj.ymin, proj.ymin+2.8*H, proj.ymin+2.8*H],
    #           '#500000',alpha=0.25,ec='none')

    ax.imshow(i,extent=(proj.xmax*.98-W,proj.xmax*.98, proj.ymin+H*.1, proj.ymin+H*1.1),zorder=1e3)
    #pl.text(proj.xmax-W/2., proj.ymin+2.2*H,'OOF',
    #           fontdict={'size':14,'family':'serif'},
    #           color='#500000',ha='center',weight='bold')

    pl.text(proj.xmax*.8, proj.ymax*(-.1),sdate.strftime("%d %b %Y"),
    #pl.text(proj.xmax*.62, proj.ymax*.93,sdate.strftime("%d %b %Y"),
               fontdict={'size':13,'family':'monospace'},ha='center')
    # change date format if tind is not daily mean, ie, add hour, etc

    if FA=='f':
      s='Pronostico desde %s' % date.strftime("%d %b %Y")
      pl.text(proj.xmax*.8, proj.ymax*(-.15),s, ##this is outside
      #pl.text(proj.xmax-W/2., proj.ymin+1.1*H,s, ##this is in the proj (inside)
                 fontdict={'fontsize':10},ha='center')
  # logo.


  # lims change in some mpl versions !!
  pl.gca().axis([proj.xmin, proj.xmax, proj.ymin, proj.ymax])

  return err,fig,info


def op_plt_wind(conf,plconf,date,FA='a',nest=0,**kargs):
  closefig = kargs.get('closefig',True)
  clearfig = kargs.get('clearfig',True)
  save     = kargs.get('save',True)

  date=dateu.parse_date(date)

  Figure,err  = opt.get_plconf(plconf,'FIGURE')

  Err=[]
  Out=[]
  pltpath = opt.nameof('out','plots',cf=conf)

  Data,err = opt.get_plconf(plconf,'WIND')

  ifig=-1
  for tag in Figure['tag']:
    ifig+=1

    args={}
    args['ifig']=ifig

    tind = Data['time'][ifig]
    if tind == 'dailyMean':
      if FA=='a': ndays=1
      elif FA=='f': ndays=int(opt.get_conf(conf,'PRED','npred')[0])

    for day in range(ndays): # loop over time:

      args['day']=day
      err,fig,info=plt_wind(conf,plconf,date,FA,nest,**args)
      Err+=[err]
      if not err:

        # save:
        if save:
          if tag: Tag='_'+tag
          else: Tag=tag
          savename='wind_%s_%s_%d_n%d%s' % (date.strftime('%Y%m%d'),FA,day,nest,Tag)

          Y,M,D=date.year,date.month,date.day
          Ydest  = os.path.join(pltpath,'%s' % Y )
          if not os.path.isdir(Ydest): os.mkdir(Ydest)
          MDdest = os.path.join(Ydest,'%02d_%02d' % (M,D) )
          if not os.path.isdir(MDdest): os.mkdir(MDdest)

          savename=os.path.join(MDdest,savename+'.'+Figure['extension'][ifig])
          Out+=[savename]

          pl.savefig(savename,dpi=pl.gcf().dpi)

        if clearfig: fig.clear()
        if closefig: pl.close(fig)

  return Err,Out


def plt0_wind_rose(conf,plconf):
  figs=[]

  Data,err   = opt.get_plconf(plconf,'WINDR')
  Places,err = opt.get_plconf(plconf,'WINDR_PLACES')
  Tag=Data['tag']
  ifig=-1
  for tag in Tag:
    ifig+=1
    figpos      = Data['fig_size'][ifig]
    axpos       = Data['ax_pos'][ifig]
    fontsize    = Data['fontsize'][ifig]
    linewidth   = Data['linewidth'][ifig]
    legType     = Data['legtype'][ifig]
    intensities = Data['intensities'][ifig]
    percentages = Data['percentages'][ifig]

    percentages=[100]
    args={'fontsize':fontsize,'linewidth':linewidth,'figpos':figpos,'axpos':axpos,'legtype':legType,'labels':0}
    D=[]
    F=[]
    tmp=pl_plots.wind_rose(D,F,di=intensities,ci=percentages,**args)
    figs+=[tmp]

  # save:
  pltpath = opt.nameof('out','plots',cf=conf)
  n=-1
  names=[]
  for f in figs:
    savename='plt0_wr'
    n+=1
    if Tag[n]: savename=savename+'_%s' % (Tag[n])
    savename=os.path.join(pltpath,savename+'.'+Data['extension'][n])
    f.savefig(savename,dpi=f.dpi)

    names+=[savename]
    pl.close(f)

  return names


def plt_wind_rose(conf,plconf,date,FA='a',nest=0,**kargs):
  err  = ''
  fig  = []
  info = []

  ifig  = kargs.get('ifig',0)
  quiet = kargs.get('quiet',0)
  place = kargs.get('place',False)
  day   = kargs.get('day','all')

  date=dateu.parse_date(date)

  # find input files:
  args={'cf':conf,'date':date,'FA':FA,'nest':nest}
  atm = opt.nameof('in','blk',**args)
  grd = opt.nameof('in','grd',**args)
  if not os.path.isfile(atm):
    err='ATM file not found (%s)' % atm
    return err,fig,info
  if not os.path.isfile(grd):
    err='Grid file not found (%s)' % grd
    return err,fig,info

  # get conf data and places:
  Data,err   = opt.get_plconf(plconf,'WINDR')
  Places,err = opt.get_plconf(plconf,'WINDR_PLACES')
  figpos      = Data['fig_size'][ifig]
  axpos       = Data['ax_pos'][ifig]
  fontsize    = Data['fontsize'][ifig]
  linewidth   = Data['linewidth'][ifig]
  legType     = Data['legtype'][ifig]
  intensities = Data['intensities'][ifig]
  percentages = Data['percentages'][ifig]
  Title       = Data['title'][ifig]
  labels      = Data['labels'][ifig]

  places={}
  for k in Places.keys(): places[k]=Places[k][ifig]

  # get data from atm file:
  f=roms.Blk(atm,grd)
  for k in places.keys():
    if place and place!=k.strip('_'): continue
    lon,lat=places[k][:2]
    Ndays=int(np.ceil(f.tdays[-1]-f.tdays[0]))
    if day=='all': Days=range(Ndays)
    else: Days=[day]

    for Day in Days:
      time,u,v = f.get('wind_ts',lon=lon,lat=lat,day=Day)

      # calc angle and intensity:
      D=np.arctan2(v,u)*180/np.pi
      F=np.sqrt(u**2+v**2)

      # wind_rose:
      args={'fontsize':fontsize,'linewidth':linewidth,'figpos':figpos,
            'axpos':axpos,'legtype':legType,'labels':labels}

      # tilte:
      if Title:
        placeStr=places[k][2]#k.strip('_').replace('_',' ')

        simpleTitle=1

        rdate=date.strftime('%d-%m-%Y')
        title='%s %s %s %d' % (placeStr,rdate,FA,Day)

        if simpleTitle: # simpler version of title:
          if FA=='f': # forecast date:
            rdate=dateu.next_date(date,Day);
            rdate=rdate.strftime('%d-%m-%Y')

          title='%s %s' % (placeStr,rdate)
          if FA=='f':
            title=title+' (forec)'

        args['labtitle']=title
        args['lablegend']='wind m/s'

      tmp=wr.wind_rose(D,F,di=intensities,ci=percentages,**args)
      fig+=[tmp]

      info+=[(k,Day)]

  return err,fig,info


def op_plt_wind_rose(conf,plconf,date,FA='a',nest=0,**kargs):
  closefig = kargs.get('closefig',True)
  clearfig = kargs.get('clearfig',True)
  save     = kargs.get('save',True)

  date=dateu.parse_date(date)

  Err=[]
  Out=[]
  pltpath = opt.nameof('out','plots',cf=conf)

  Data,err = opt.get_plconf(plconf,'WINDR')

  ifig=-1
  for tag in Data['tag']:
    ifig+=1

    args={}
    args['ifig']=ifig

    err,figs,info=plt_wind_rose(conf,plconf,date,FA,nest,**args)
    if not err:
      # save:
      if save:
        if tag: Tag='_'+tag
        else: Tag=tag

        tmp=dateu.parse_date(date)
        Y,M,D=tmp.year,tmp.month,tmp.day
        Ydest  = os.path.join(pltpath,'%s' % Y )
        if not os.path.isdir(Ydest): os.mkdir(Ydest)
        MDdest = os.path.join(Ydest,'%02d_%02d' % (M,D) )
        if not os.path.isdir(MDdest): os.mkdir(MDdest)

        N=-1
        for fig in figs:
          N+=1
          place,day=info[N]
          savename='wind_rose_%s_%s_%d_%s_n%d%s' % (date,FA,day,place,nest,Tag)

          savename=os.path.join(MDdest,savename+'.'+Data['extension'][ifig])
          Out+=[savename]

          fig.savefig(savename,dpi=fig.dpi)

          if clearfig: fig.clear()
          if closefig: pl.close(fig)

  return Err,Out


def op_plt(conf,plconf,date,FA,nest=0,**kargs):
  herr=hout=ferr=fout=werr=wout=wrerr=wrout=[]
  flags=opt.flags_info(plconf)

  data=dateu.parse_date(date)

  hcond  = (FA=='a' and flags['hslicesa']) or (FA=='f' and flags['hslicesf'])
  fcond  = (FA=='a' and flags['floatsa'])  or (FA=='f' and flags['floatsf'])
  wcond  = (FA=='a' and flags['winda'])    or (FA=='f' and flags['windf'])
  wrcond = (FA=='a' and flags['windra'])   or (FA=='f' and flags['windrf'])

  if 'vname' in kargs.keys():
    hcond  = kargs['vname'] in ('temp','salt','zeta') or kargs['vname'].startswith('dye')
    fcond  = kargs['vname']=='floats'
    wcond  = kargs['vname']=='wind'
    wrcond = kargs['vname']=='windr'
    if hcond:  fcond,wcond,wrcond = False,False,False
    if fcond:  hcond,wcond,wrcond = False,False,False
    if wcond:  hcond,fcond,wrcond = False,False,False
    if wrcond: hcond,fcond,wcond  = False,False,False

  if hcond:  herr, hout  = op_plt_hslice(conf,plconf,date,FA,nest,**kargs)
  if fcond:  ferr, fout  = op_plt_flt(conf,plconf,date,FA,nest,**kargs)
  if wcond:  werr, wout  = op_plt_wind(conf,plconf,date,FA,nest,**kargs)
  if wrcond: wrerr,wrout = op_plt_wind_rose(conf,plconf,date,FA,nest,**kargs)

  return herr+ferr+werr+wrerr,hout+fout+wout+wrout


def op_plt_many(conf,plconf,startDate,endDate,FA=('a','f'),**kargs):
  startDate=dateu.parse_date(startDate)
  endDate=dateu.parse_date(endDate)
  date=dateu.next_date(startDate,-1)
  while endDate>date:
    date=dateu.next_date(date)
    for p in FA:
      errs,names=op_plt(conf,plconf,date,FA=p,**kargs)
      for e,n in zip(errs,names):
        print e,n


