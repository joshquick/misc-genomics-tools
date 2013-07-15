import vcf
import sys
import re
from collections import defaultdict
from optparse import OptionParser
import operator

def read_table(fn):
	table = []
	colnames = []
	headers = False
	for ln in open(fn):
		ln = ln.rstrip()
		if ln.startswith('#') and headers == False:
			colnames = ln[1:].split("\t")
			headers = True
			continue
		if ln.startswith('#'):
			continue
		cols = ln.split("\t")
		d = {}
		for key in colnames:
			d[key] = ''
			for n, v in enumerate(cols):
				try:
					d[colnames[n]] = v
				except:
					print >>sys.stderr, "Warning misformed %s" % (ln,)
		table.append(d)
	return colnames, table

def go(args, options):
	metadata_columns, metadata = read_table(options.metadata)
	fh_alleles = open("alleles.txt", "w")
	fh_samples = open("samples.txt", "w")

	alleles = defaultdict(str)
	nocalls = defaultdict(int)
	nocalls_by_rec = defaultdict(list)
	nocalls_list = []

	vcf_reader = vcf.Reader(open(args[0]), "r")
	vcf_records = list(vcf_reader)

	for record in vcf_records:
		for sample in record.samples:
			if sample.gt_bases is None:
				nocalls[sample.sample] += 1

				nocalls_by_rec["%s-%s" % (record.CHROM, record.POS)].append(sample)

				nocalls_list.append([record.CHROM, record.POS, record.REF, record.ALT, sample.sample, sample.data.SDP])

	ignore_samples = []
	total_records = float(len(vcf_records))
	for sample, num_nocalls in nocalls.iteritems():
		perc = float(num_nocalls) / total_records * 100
		if perc > options.percent_nocalls:
			ignore_samples.append(sample)

	print "Samples to ignore: %s" % (", ".join(ignore_samples))

	for record in vcf_records:
		samples_to_use = [sample for sample in record.samples if sample.sample not in ignore_samples]
		bases = [sample.gt_bases for sample in samples_to_use if sample.gt_bases is not None]
	
		if len(bases) != len(samples_to_use):
			continue

		incorrect_lengths = [sample for sample in samples_to_use if len(sample.gt_bases.split("/")[0]) != 1]

		if incorrect_lengths: ## e.g. indels
			continue	

		for sample in samples_to_use:
			alleles[sample.sample] += sample.gt_bases.split("/")[0]

# unique allele number	
	unique_alleles = set(alleles.values())
	allele_lookup = dict([(allele, n+1) for n, allele in enumerate(unique_alleles)])

# founder
	allele_lookup = {}
	for sample, genotype in alleles.iteritems():
		if genotype not in allele_lookup:
			allele_lookup[genotype] = sample

	print >>fh_samples, "Sample\tProfile\t",
	print >>fh_samples, "\t".join(metadata_columns)
	for sample, genotype in alleles.iteritems():
		print >>fh_samples, "%s\t%s\t" % (sample, allele_lookup[genotype]) ,
		for sample_metadata in metadata:
			if sample_metadata['Sample'] == sample:
				print >>fh_samples, "\t".join([sample_metadata[key] for key in metadata_columns if key != 'Sample']) ,
		print >>fh_samples

	for allele, allele_number in allele_lookup.iteritems():
		print >>fh_alleles, ">%s\n%s" % (allele_number, allele)

	for sample, value in sorted(nocalls.iteritems(), key=operator.itemgetter(1)):
		print "%s => %s" % ( sample, value )

#	for loc, samplelist in sorted(nocalls_by_rec.iteritems(), key=operator.itemgetter(1)):
#		print "%s: " % (loc,)
# 		for sample in samplelist:
#			print "   %s" % (sample)

	if options.nocallsfile:
		nocall_fh = open(options.nocallsfile, "w")
		print >>nocall_fh, "CHROM\tPOS\tREF\tALT\tSample\tSDP"
		for nocall in nocalls_list:
			print >>nocall_fh, "\t".join([str(s) for s in nocall])
		nocall_fh.close()

def main():
	usage = "usage: %prog [options] vcffile"
	parser = OptionParser(usage)
	parser.add_option("-m", "--metadata", dest="metadata",
					  help="load metadata from METADATA")
	parser.add_option("-s", "--samples", dest="samplefile",
					  help="output sample info to SAMPLEFILE (default: <vcffile>_samples.txt")
	parser.add_option("-a", "--alleles", dest="allelesfile",
					  help="output alleles file to ALLELESFILE (default: <vcffile>_alleles.txt")
        parser.add_option("-n", "--nocalls", dest="nocallsfile",
                                          help="output alleles file to NOCALLSFILE (default: <vcffile>_nocalls.txt")
	parser.add_option("-p", "--percentage_nocalls", dest="percent_nocalls", type="float", default=0.0,
					  help="do not include samples with greater than <percentnocall> no calls")
	parser.add_option("-v", "--verbose",
					  action="store_true", dest="verbose")
	parser.add_option("-q", "--quiet",
					  action="store_false", dest="verbose")

	(options, args) = parser.parse_args()
	if len(args) != 1:
		parser.error("incorrect number of arguments")
	if options.verbose:
		print "reading %s..." % options.filename

	go(args, options)

if __name__ == "__main__":
	main()

