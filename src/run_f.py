#!/usr/bin/python -u
import sys
from os.path import join

here=sys.path[0]
sys.path.append(join(here,'oof'))


cf=join(here,'oof','oof.conf')
pf=join(here,'oof','plots.conf')

from engine import oof

def run():
  oof.oof(cf,pf,FA='f')
  # env variables, needed for model, may be added here. ex:
  # oof(...,env={'OMP_NUM_THREADS':'24'})


if __name__=='__main__':
  run()

