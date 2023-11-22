#!/usr/bin/python3
# -*- coding: utf-8 -*-

'''
Goal: Enable the generation of a noisier instance of an acquisition by either dropping
times block or events.


TODO:
	Core:
		- Singles rates is not ajusted.
		- Dead times measurement is not dealt with.
	Feature:
		- Quicker algo
'''

#########################################################################################
# Modules
#########################################################################################
import argparse
import prd
import random
import sys
from typing import Union


#########################################################################################
# Methods
#########################################################################################
def defineWriter(oFile: Union[str, None], verbose: int):
	if oFile is None:
		if verbose > 0:
			print("Warning: if the output is redirected into a file, the verbosity "
			      "might break the file produced.")
			input("Press Enter to continue...")
		return sys.stdout.buffer
	else:
		return oFile

def sampleByTimeBlock(cTimeBlock, retFrac: float):
	if random.random() < retFrac:
		return (cTimeBlock,), None
	else:
		return None

def sampleByEvent(cTimeBlock, retFrac: float):
	keptPrompt = []
	for cPr in cTimeBlock.prompt_events:
		if random.random() < retFrac:
			keptPrompt.append(cPr)

	if cTimeBlock.delayed_events is not None:
		keptDelay = []
		for cDl in cTimeBlock.delayed_events:
			if random.random() < retFrac:
				keptDelay.append(cDl)
		nbKeptDelay = len(keptDelay)
	else:
		keptDelay = None
		nbKeptDelay = 0

	stats = (len(keptPrompt), nbKeptDelay)

	return (prd.TimeBlock(id=time_block.id, prompt_events=keptPrompt,
								delayed_events=keptDelay),), stats



def providBasicStat(verbose: int, randoMethod: str, nbTimeBlock: int,
	                nbTimeBlockKept: int, nbPrompt: int, nbPromptKept: int, nbDelay: int,
	                nbDelayKept: int):

	if verbose > 0 and randoMethod == "timeBlock":
		print(f"Number of time block kept {nbTimeBlockKept} out of {nbTimeBlock}. " +
				f"In percent: {(nbTimeBlockKept / nbTimeBlock) * 100.0}%")

	if verbose > 0 and randoMethod == "event":
		print(f"Number of prompt kept {nbPromptKept} out of {nbPrompt}. " +
				f"In percent: {(nbPromptKept / nbPrompt) * 100.0}%")
		if nbDelay != 0:
			print(f"Number of delays kept {nbDelayKept} out of {nbDelay}. " +
					f"In percent: {(nbDelayKept / nbDelay) * 100.0}%")



#########################################################################################
# Scripting functionnality
#########################################################################################
def parserCreator():
	parser = argparse.ArgumentParser(description="Sample an anquisition file to produce "
	                "a new version of the acquisition with less statistics.")

	##################################################
	# Basic
	parser.add_argument('--acqFile', action='store', type=str, required=True,
	                    dest='acq',
	                    help='The acquisition, in PETSIRD format, to sample from.')
	parser.add_argument('-r', '--retentionFrac', action='store', type=float,
	                    required=True, dest='retFrac',
	                    help='The expected fraction of retend events/time blocks.')
	parser.add_argument('-m', '--randoMethod', action='store',
	                    choices=["event", "timeBlock"], default="timeBlock",
	                    dest='randoMethod',
	                    help='The method used for retention of events.')
	parser.add_argument('-o', '--outputFile', action='store', type=str,
	                    default=None, dest='oFile',
	                    help='The path/name where to save the resulting list mode. If '
	                         'it is not defined, it will be written in the std.out.')

	##################################################
	# Feature
	parser.add_argument('-s', '--seed', action='store', type=int, default=None,
	                    dest='seed',
	                    help='Set the seed used for retention method.')
	parser.add_argument('-v', '--verbose', action='store', type=int, default=0,
	                    dest='verbose',
	                    help='Level of verbosity of the script.')

	return parser.parse_args()



#########################################################################################
# Test functions
#########################################################################################
# n/a


#########################################################################################
# main
#########################################################################################
if __name__ == "__main__":
	args = parserCreator()

	if args.seed is not None:
		random.seed(args.seed)

	writerOutput = defineWriter(args.oFile, args.verbose)

	if args.randoMethod == "timeBlock":
		sampler = lambda timeBlock: sampleByTimeBlock(timeBlock, args.retFrac)
	elif args.randoMethod == "event":
		sampler = lambda timeBlock: sampleByEvent(timeBlock, args.retFrac)

	with prd.BinaryPrdExperimentWriter(writerOutput) as writer:
		reader = prd.BinaryPrdExperimentReader(args.acq)
		header = reader.read_header()
		writer.write_header(header)

		# Variable for basic static
		nbTimeBlock = 0
		nbTimeBlockKept = 0
		nbPrompt = 0
		nbPromptKept = 0
		nbDelay = 0
		nbDelayKept = 0
		for tbID, time_block in enumerate(reader.read_time_blocks()):
			nbTimeBlock += 1
			nbPrompt += len(time_block.prompt_events)
			if time_block.delayed_events is not None:
				nbDelay += len(time_block.delayed_events)

			res = sampler(time_block)
			if res is not None:
				resTimeBlock, stats = res
				writer.write_time_blocks(resTimeBlock)
				if args.randoMethod == "timeBlock":
					nbTimeBlockKept += 1
				elif args.randoMethod == "event":
					nbPromptKept += stats[0]
					nbDelayKept += stats[1]

	providBasicStat(args.verbose, args.randoMethod, nbTimeBlock, nbTimeBlockKept,
					nbPrompt, nbPromptKept, nbDelay, nbDelayKept)

	# If the list mode is empty, we still create a valid list mode
	if (nbTimeBlockKept == 0) and (nbPromptKept == 0):
		print("Warning: No prompt or time block were preserved")
		tmp = (prd.TimeBlock(id=0, prompt_events=[]), )
		writer.write_time_blocks(tmp)
