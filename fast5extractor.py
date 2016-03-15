#!/usr/bin/env python

'''
reads event data from ONT fast5 file, writes event data matrix to output.

Copyright 2016, David Eccles (gringer) <bioinformatics@gringene.org>

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted. The software is
provided "as is" and the author disclaims all warranties with regard
to this software including all implied warranties of merchantability
and fitness. In other words, the parties responsible for running the
code are solely liable for the consequences of code execution.
'''

import os
import sys
import h5py
import numpy
from collections import Counter

def generate_event_matrix(fileName, header=True):
    '''write out event matrix from fast5, return False if not present'''
    try:
        h5File = h5py.File(fileName, 'r')
        h5File.close()
    except:
        return False
    with h5py.File(fileName, 'r') as h5File:
      runMeta = h5File['UniqueGlobalKey/tracking_id'].attrs
      channelMeta = h5File['UniqueGlobalKey/channel_id'].attrs
      runID = '%s_%s' % (runMeta["device_id"],runMeta["run_id"][0:16])
      eventBase = "/Analyses/EventDetection_000/Reads/"
      readNames = h5File[eventBase]
      for readName in readNames:
        readMetaLocation = "/Analyses/EventDetection_000/Reads/%s" % readName
        eventLocation = "/Analyses/EventDetection_000/Reads/%s/Events" % readName
        outMeta = h5File[readMetaLocation].attrs
        channel = str(channelMeta["channel_number"])
        mux = str(outMeta["start_mux"])
        headers = h5File[eventLocation].dtype
        outData = h5File[eventLocation][()] # load entire array into memory
        if(header):
            sys.stdout.write("runID,channel,mux,read,"+",".join(headers.names)+"\n")
        # There *has* to be an easier way to do this while preserving
        # precision. Reading element by element seems very inefficient
        for line in outData:
          res=map(str,line)
          # data seems to be normalised, but just in case it isn't, here's the formula for
          # future reference: pA = (raw + offset)*range/digitisation
          # (using channelMeta[("offset", "range", "digitisation")])
          sys.stdout.write(",".join((runID,channel,mux,readName)) + "," + ",".join(res) + "\n")

def generate_fastq(fileName, callID="000"):
    '''write out fastq sequence(s) from fast5, return False if not present'''
    try:
        h5File = h5py.File(fileName, 'r')
        h5File.close()
    except:
        return False
    with h5py.File(fileName, 'r') as h5File:
      runMeta = h5File['UniqueGlobalKey/tracking_id'].attrs
      channelMeta = h5File['UniqueGlobalKey/channel_id'].attrs
      runID = '%s_%s' % (runMeta["device_id"],runMeta["run_id"][0:16])
      eventBase = "/Analyses/EventDetection_%s/Reads/" % callID
      readNames = h5File[eventBase]
      channel = -1
      mux = -1
      readNameStr = ""
      for readName in readNames:
        readMetaLocation = "/Analyses/EventDetection_000/Reads/%s" % readName
        eventLocation = "/Analyses/EventDetection_000/Reads/%s/Events" % readName
        outMeta = h5File[readMetaLocation].attrs
        channel = str(channelMeta["channel_number"])
        mux = str(outMeta["start_mux"])
        readNameStr = str(readName)
      seqBase1D = "/Analyses/Basecall_1D_%s" % callID
      seqBase2D = "/Analyses/Basecall_2D_%s" % callID
      badEvt = False
      if(seqBase1D in h5File):
          baseComp = "%s/BaseCalled_complement/Fastq" % seqBase1D
          baseTemp = "%s/BaseCalled_template/Fastq" % seqBase1D
          eventComp = "%s/BaseCalled_complement/Events" % seqBase1D
          eventTemp = "%s/BaseCalled_template/Events" % seqBase1D
          if(eventTemp in h5File):
              headers = h5File[eventTemp].dtype
              moveLoc = -1
              for index, item in enumerate(headers.names):
                  if(item == "move"):
                      moveLoc = index
              outEvt = h5File[eventTemp][:] # load events into memory
              mCount = Counter(map(lambda x: x[moveLoc], outEvt))
              badThresh = (sum(mCount.values()) * 0.05)
              #sys.stdout.write("#%s\n" % str(mCount))
              if(((mCount[0] + mCount[2]) < (badThresh*4)) and
                 ((mCount[3] + mCount[4] + mCount[5] + mCount[6]) < badThresh) and (baseTemp in h5File)):
                  sys.stdout.write("@1Dtemp_"+
                                   "_".join((runID,channel,mux,readName)) + " ")
                  sys.stdout.write(str(h5File[baseTemp][()][1:]))
              else:
                  badEvt = True
          if(eventComp in h5File):
              headers = h5File[eventComp].dtype
              moveLoc = -1
              for index, item in enumerate(headers.names):
                  if(item == "move"):
                      moveLoc = index
              outEvt = h5File[eventComp][:] # load events into memory
              mCount = Counter(map(lambda x: x[moveLoc], outEvt))
              badThresh = (sum(mCount.values()) * 0.05)
              #sys.stdout.write("#%s\n" % str(mCount))
              if(((mCount[0] + mCount[2]) < badThresh*4) and
                 ((mCount[3] + mCount[4] + mCount[5] + mCount[6]) < badThresh) and (baseComp in h5File)):
                  sys.stdout.write("@1Dcomp_"+
                                   "_".join((runID,channel,mux,readName)) + " ")
                  sys.stdout.write(str(h5File[baseComp][()][1:]))
              else:
                  badEvt = True
      else:
          sys.stderr.write("seqBase1D [%s] not in file\n" % seqBase1D)
      if((not badEvt) and seqBase2D in h5File):
          base2D = "%s/BaseCalled_2D/Fastq" % seqBase2D
          if((base2D in h5File)):
              sys.stdout.write("@2Dcons_"+
                           "_".join((runID,channel,mux,readName)) + " ")
              sys.stdout.write(str(h5File[base2D][()][1:]))

if len(sys.argv) < 3:
    sys.stderr.write('Usage: %s <dataType> <fast5 file name>\n' % sys.argv[0])
    sys.stderr.write('  where <dataType> is one of {fastq, event, raw}\n')
    sys.exit(1)

dataType = sys.argv[1]
if(not dataType in ("fastq","fasta","event","raw")):
    sys.stderr.write('Error: Incorrect dataType\n\n')
    sys.stderr.write('Usage: %s <dataType> <fast5 file name>\n' % sys.argv[0])
    sys.stderr.write('  where <dataType> is one of {fastq, event, raw}\n')
    sys.exit(1)

fileArg = sys.argv[2]
seenHeader = False

if(os.path.isdir(fileArg)):
    sys.stderr.write("Processing directory '%s':\n" % fileArg)
    for dirPath, dirNames, fileNames in os.walk(fileArg):
        fc = len(fileNames)
        for fileName in fileNames:
            if(fileName.endswith(".fast5")): # only process fast5 files
                sys.stderr.write("  Processing file '%s'..." % fileName)
                if(dataType == "event"):
                    generate_event_matrix(os.path.join(dirPath, fileName), not seenHeader)
                elif(dataType == "fastq"):
                    generate_fastq(os.path.join(dirPath, fileName))
                fc -= 1
                seenHeader = True
                if(fc == 1):
                    sys.stderr.write(" done (%d more file to process)\n" % fc)
                else:
                    sys.stderr.write(" done (%d more files to process)\n" % fc)
elif(os.path.isfile(fileArg)):
    if(dataType == "event"):
        generate_event_matrix(fileArg)
    elif(dataType == "fastq"):
        generate_fastq(fileArg)
else:
    sys.stderr.write('Error: No file or directory provided in arguments\n\n')
    sys.stderr.write('Usage: %s <dataType> <fast5 file name>\n' % sys.argv[0])
    sys.stderr.write('  where <dataType> is one of {fastq, event, raw}\n')
    sys.exit(1)
