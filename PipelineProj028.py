import pandas as pd
import numpy as np
import CGAT.IOTools as IOTools
from CGATPipelines.Pipeline import cluster_runnable
import CGATPipelines.PipelineUtilities as PUtils
import CGAT.Experiment as E
import CGAT.GTF as GTF
import CGAT.Bed as Bed
import CGAT.FastaIterator as FastaIterator
import iCLIP
import CGAT.Intervals as Intervals
import collections
import pysam
import re
import xml
import os
import itertools

AMBIGUITY_CODES = {'M': 'AC',
                   'R': 'AG',
                   'W': 'AT',
                   'S': 'CG',
                   'Y': 'CT',
                   'K': 'GT',
                   'V': 'ACG',
                   'H': 'ACT',
                   'D': 'AGT',
                   'B': 'CGT',
                   'N': 'CGAT'}


def IUPAC2Regex(sequence):

    for code, regex in AMBIGUITY_CODES.iteritems():
        sequence = re.sub(code, '[%s]' % regex, sequence)

    return sequence


@cluster_runnable
def normalizeIndevidualProfilesToRNASeq(clip_profile_file,
                                        rnaseq_profile_file,
                                        outfile_matrix,
                                        outfile_summary,
                                        pseduo_count=1):

    clip_profile = pd.read_csv(IOTools.openFile(clip_profile_file),
                               sep="\t",
                               index_col=0)
    rnaseq_profile = pd.read_csv(IOTools.openFile(rnaseq_profile_file),
                                 sep="\t",
                                 index_col=0)

    rnaseq_profile = rnaseq_profile + pseduo_count

    normalised_profile = clip_profile/rnaseq_profile
    
    normalised_profile = normalised_profile.apply(lambda x:
                                                  x/x.sum(),
                                                  axis=1)

    average_profile = normalised_profile.sum()

    normalized_average_profile = average_profile/average_profile.sum()

    normalised_profile.to_csv(IOTools.openFile(outfile_matrix, "w"),
                              sep="\t",
                              index_label="Transcript")
    normalized_average_profile.name = "profile"
    normalized_average_profile.to_csv(IOTools.openFile(outfile_summary, "w"),
                                      header=True,
                                      sep="\t",
                                      index_label="position")


@cluster_runnable
def getSingleExonProfiles(clip_profile_file,
                          rnaseq_profile_file,
                          outfile_matrix,
                          outfile_summary,
                          annotations,
                          pseduo_count=1):

    statement = ''' SELECT DISTINCT es.transcript_id as id,
                    FROM exon_stats as es
                    INNER JOIN transcript_info as ti
                    ON es.transcript_id = ti.transcript_id
                    GROUP BY ti.gene_id
                    HAVING MAX(nval) = 1 '''

    single_exon_genes = PUtils.fetch_DataFrame(statement, annotations)
    single_exon_genes = single_exon_genes["id"].values

    clip_profile = pd.read_csv(IOTools.openFile(clip_profile_file),
                               sep="\t",
                               index_col=0)

    single_exon_clip_profiles = clip_profile.loc[single_exon_genes]
    
    rnaseq_profiles = pd.read_csv(IOTools.openFile(rnaseq_profile_file),
                                  sep = "\t",
                                  index_col=0)

    single_exon_rnaseq_profiles = rnaseq_profiles.loc[single_exon_genes] + pseduo_count

    normalised_profile = single_exon_clip_profiles/single_exon_rnaseq_profiles
    
    normalised_profile = normalised_profile.apply(lambda x:
                                                  x/x.sum(),
                                                  axis=1)

    average_profile = normalised_profile.sum()

    normalized_average_profile = average_profile/average_profile.sum()

    normalised_profile.to_csv(IOTools.openFile(outfile_matrix, "w"),
                              sep="\t",
                              index_label="Transcript")
    normalized_average_profile.name = "profile"
    normalized_average_profile.to_csv(IOTools.openFile(outfile_summary, "w"),
                                      header=True,
                                      sep="\t",
                                      index_label="position")
    

    
@cluster_runnable
def clusterStats(bedGraph_file, gtf_file, outfile):

    bedGraph = pd.read_csv(IOTools.openFile(bedGraph_file),
                           sep="\t",
                           names=["chr","pos","q"])

    bedGraph.q = bedGraph.q.replace(0, 1)
    
    bedGraph = bedGraph.set_index(["chr", "pos"])
    bedGraph = bedGraph.sort_index()

    num_sig = (bedGraph < 0.05).sum()
    sig_exon_count = 0
    sig_intron_count = 0
    sig_gene_count = 0

    for gene in GTF.flat_gene_iterator(GTF.iterator(IOTools.openFile(gtf_file))):
        
        introns = GTF.toIntronIntervals(gene)
        exons = GTF.asRanges(gene)

        exons = Intervals.combine(exons)

        for exon in exons:
            
            if (bedGraph[exon[0]:exon[1]] < 0.05).sum() > 0:
                sig_exons = True
                break

        for intron in introns:
            if (bedGraph[gene.contig][intron[0]:intron[1]] < 0.05).sum() > 0:
                sig_introns = True
                break

        if sig_exons:
            sig_exon_count += 1

        if sig_introns:
            sig_intron_count += 1

        if sig_introns or sig_exons:
            sig_gene_count += 1

    with IOTools.openFile(outfile, "w") as outf:

        outf.write("Significant bases:\t%s" % num_sig)
        outf.write("Significant genes:\t%s" % sig_gene_count)
        outf.write("Genes with signfficant exons:\t%s" % sig_exon_count)
        outf.write("Genes with significant introns:\t%s" % sig_intron_count)


@cluster_runnable
def averageRegions(infile, resolutions, outfile):

    count_matrix = IOTools.openFile(infile)

    count_matrix.readline()

    outdict = collections.defaultdict(list)

    for line in count_matrix:

        fields = line.split("\t")
 
        gene_id, fields = fields[0], map(float, fields[1:])

        averages = []
        start = 0

        for i in range(len(resolutions)):
            end = start+resolutions[i]
            averages.append(np.mean(fields[start:end]))
            start = end

        outdict["transcript_id"].append(gene_id)
        outdict["upstream"].append(averages[0])
        outdict["5utr"].append(averages[1])
        outdict["CDS"].append(averages[2])
        outdict["3utr"].append(averages[3])
        outdict["downstream"].append(averages[4])

    pd.DataFrame(outdict).to_csv(IOTools.openFile(outfile, "w"),
                                 sep="\t",
                                 index=False)


def scoreRegions(summary_df):

    summary_df.drop("Protein", axis=1, inplace=True)
    summary_df = summary_df.set_index(["Replicate", "transcript_id"])

    summary_df.drop("R1", axis=0, inplace=True)
    summary_df.replace("nan", np.nan, inplace = True)
    df_average = summary_df.groupby(level="transcript_id").mean()
    df_logrank = df_average.rank().apply(np.log10)
    print df_logrank.head()
    df_score = pd.DataFrame({"cds": df_logrank["cds_enrichment"] + df_logrank["cds_count"],
                             "utr3": df_logrank["utr3_enrichment"] + df_logrank["utr3_count"],
                             "utr5": df_logrank["utr5_enrichment"] + df_logrank["utr5_count"]})

    return df_score


@cluster_runnable
def scoreCircularCandidates(outfile):

    statement = ''' SELECT * FROM profile_summaries
                    WHERE Protein='%s' '''

    chtop = PUtils.fetch_DataFrame(statement % "Chtop")
    alyref = PUtils.fetch_DataFrame(statement % "Alyref")
   
    chtop_score = scoreRegions(chtop)
    alyref_score = scoreRegions(alyref)

    clip_score = chtop_score["utr3"] + alyref_score["utr5"]

    clip_score.to_csv(IOTools.openFile(outfile, "w"),
                      sep = "\t",
                      index_label=True)


   
@cluster_runnable
def calculateRegionEnrichments(bamfile, gtffile, outfile):

    import pysam
    import iCLIP

    bam = pysam.Samfile(bamfile)
    outlines = []

    for transcript in GTF.transcript_iterator(
            GTF.iterator(IOTools.openFile(gtffile))):

        regions = pd.Series()
        exons = GTF.asRanges(transcript, "exon")
        regions["cds"] = GTF.asRanges(transcript, "CDS")

        # skip genes without cds
        if len(regions["cds"]) == 0:
            continue

        utrs = Intervals.truncate(exons, regions["cds"])

        cds_start, cds_end = regions["cds"][0][0], regions["cds"][-1][1]

        if transcript[0].strand == "+":
            regions["utr3"] = [x for x in utrs if x[0] >= cds_end]
            regions["utr5"] = [x for x in utrs if x[0] <= cds_start]
        else:
            regions["utr3"] = [x for x in utrs if x[0] <= cds_start]
            regions["utr5"] = [x for x in utrs if x[0] >= cds_end]

        # check that there is both a 3 and a 5' utr
        if any(regions.apply(len) == 0):
            continue

        # Do the counting:
        region_counts = regions.apply(lambda x:
                                      iCLIP.count_intervals(
                                          bam,
                                          x,
                                          transcript[0].contig,
                                          transcript[0].strand))

        region_counts = region_counts.sum(axis=1)
        region_counts = region_counts.fillna(0)

        transcript_length = sum([x[1] - x[0] for x in exons])

        region_lengths = regions.apply(lambda region: sum(
            [exon[1] - exon[0]
             for exon in region]))

        fractional_lengths = region_lengths/transcript_length
        fractional_counts = region_counts/region_counts.sum()

        enrichments = fractional_counts/fractional_lengths

        region_lengths = region_lengths.sort_index()
        region_counts = region_counts.sort_index()
        enrichments = enrichments.sort_index()

        outline = [transcript[0].transcript_id] + \
                  list(region_lengths.values) + \
                  list(region_counts.values) + \
                  list(enrichments.values) 

        outlines.append(outline)
    
    region_names = sorted(["cds", "utr5", "utr3"])
    header = ["transcript_id"] + \
             [x+"_length" for x in region_names] + \
             [x+"_count" for x in region_names] + \
             [x+"_enrichment" for x in region_names]

    PUtils.write(outfile, outlines, header)


@cluster_runnable
def getTranscriptTypeByGeneID(infile, outfile):

    import CGAT.GTF as GTF
    
    outlines = []
    for transcript in GTF.transcript_iterator(
            GTF.iterator(IOTools.openFile(infile))):
        outlines.append([transcript[0].gene_id,
                         transcript[0].transcript_id,
                         transcript[0].source])

    PUtils.write(outfile, outlines,
                 header=["gene_id", "transcript_id", "biotype"])

    
@cluster_runnable
def getZagrosRIInputFiles(clusters_file, ri_file, bam_file,
                          target_length,
                          outfiles):
    '''This function takes in a set of clusters and retained introns and
    outputs the input files needed to run zagros, namely:

       Zagros compatible regions: Must all be the same length, and truncated
                                  where possible at the edges of the intron.
                                  
                                  For clusters longer than the specification,
                                  a section of the cluster will be taken so as
                                  to put the new cluster as close to centred
                                  over its maximum height as possible without
                                  including new sequence.

                                  For clusters shorter than the specification,
                                  clusters will be grown on either side until
                                  they hit intron boundaries. If the intron is
                                  smaller than the cluster size, then the 
                                  cluster will be centered on the centre of the
                                  intron.

      Zagros diagnostic events:   for each cluster region, a comma-seperated 
                                  list of mapping heights '''

    clusters = Bed.iterator(IOTools.openFile(clusters_file))
    ris = Bed.readAndIndex(IOTools.openFile(ri_file), with_values=True)
    bam = pysam.Samfile(bam_file)

    clusters_out_fn, des_fn = outfiles

    clusters_out = IOTools.openFile(clusters_out_fn, "w")
    des_out = IOTools.openFile(des_fn, "w")

    for cluster in clusters:

        E.debug("New cluster. Name %s" % cluster.name)
        cluster_depth = iCLIP.count_intervals(bam,
                                              [(cluster.start, cluster.end)],
                                              cluster.contig,
                                              cluster.strand)

        # skip clusters which just have overlapping edges
        if cluster_depth.sum() == 0:
            continue
        overlapping_ris = ris[cluster.contig].find(cluster.start, cluster.end)
       
        for intron in overlapping_ris:

            if not intron[2].strand == cluster.strand:
                continue

            cluster_length = cluster.end-cluster.start
            new_cluster = cluster.copy()
            intron_length = intron[1] - intron[0]
            E.debug("Cluster length = %s, intron length %s"
                    % (cluster_length, intron_length))
            while not cluster_length == target_length:
                if (cluster_length < target_length and
                   cluster_length < intron_length):
                    E.debug("Cluster is too short. Space to expand")
                    E.debug("Cluster is (%s,%s), intron is (%s,%s)" %
                            (new_cluster.start, new_cluster.end,
                             intron[0], intron[1]))
                    difference = target_length - cluster_length

                    right_shift = min((difference+1)/2,
                                      intron[1] - new_cluster.end)
                    E.debug("Shifting right boundary %s bases left"
                            % right_shift)
                    remainder = (difference+1)/2 - right_shift
                    new_cluster.end += right_shift

                    left_shift = min(difference/2 + remainder,
                                     new_cluster.start - intron[0])
                    new_cluster.start = new_cluster.start - left_shift
                    remainder = difference/2 + remainder - left_shift
                    E.debug("shifting left boundary %s bases left"
                            % left_shift)
                    new_cluster.end += min(remainder, intron[1] - new_cluster.end)
                    E.debug("shifting right boundary %s bsaes right" %
                            min(remainder, intron[1] - new_cluster.end))

                elif (cluster_length > target_length and
                      cluster_length < intron_length):
                    E.debug("cluster is too long. Intron is long enough")
                    cluster_peak = cluster_depth.idxmax()
                    intron = (new_cluster.start, new_cluster.end)
                    new_cluster.start = int(cluster_peak)
                    new_cluster.end = int(cluster_peak + 1)

                elif cluster_length >= intron_length:
                    E.debug("cluster is longer than intron")
                    intron_centre = (intron[1] + intron[0])/2
                    E.debug("intron centre is %i" % intron_centre)
                    new_cluster.start = intron_centre - target_length/2
                    new_cluster.end = intron_centre + (target_length+1)/2

                else:
                    raise ValueError(
                        "This shouldn't happen\n"
                        "cluster length is %s. intron length is %s")

                cluster_length = new_cluster.end-new_cluster.start
                E.debug("new cluster length is %s" % cluster_length)

            clusters_out.write("%s\n" % str(new_cluster))
            new_depth = cluster_depth.reindex(np.arange(new_cluster.start,
                                                        new_cluster.end),
                                              fill_value=0)
            des_out.write(','.join(map(str, new_depth.values)) + "\n")

    clusters_out.close()
    des_out.close()


@cluster_runnable
def findRegexMotifs(motifs_file, sequences, outtable, gfffile, len_thresh=0,
                    enrich_thresh=1):
    '''Take a DREME XML motifs file and a FASTA database and find the locations
    of motif matches in the database. Will extract location and gene infomation
    from the sequence file. '''

    motifs = []
    outlines = []
    outgffs = []
    
    tree = xml.etree.ElementTree.ElementTree()
    tree.parse(motifs_file)
    
    model = tree.find("model")
    num_positives = int(model.find("positives").get("count"))
    num_negatives = int(model.find("negatives").get("count"))
    
    for motif in tree.find("motifs").getiterator("motif"):
        p = float(motif.get("p"))
        n = float(motif.get("n"))
        try:
            enrichment = (p/num_positives)/(n/num_negatives)
            if enrichment < enrich_thresh:
                continue   
        except ZeroDivisionError:
            pass

        motif_seq = motif.get("seq")

        if len(motif_seq) < len_thresh:
            continue

        motifs.append(motif_seq)

    E.info("found %i motifs" % len(motifs))
    
    for sequence in FastaIterator.iterate(IOTools.openFile(sequences)):
        # search for coord-like fields in the name

        loc_pattern = "(chr[^\W_]+)[\W_]([0-9]+)[\W_]{1,2}([0-9]+)"
        strand_pattern = "[\W\_]\(?([+-])\)?"
        if re.search(loc_pattern + strand_pattern, sequence.title):
            pattern = loc_pattern + strand_pattern
            chrom, start, end, strand = re.search(
                pattern, sequence.title).groups()
            start, end = (int(start), int(end))
            name = re.sub(pattern, "", sequence.title)

        elif re.search(loc_pattern, sequence.title):
            pattern = loc_pattern
            strand = "+"
            chrom, start, end = re.search(pattern, sequence.title).groups()
            start, end = (int(start), int(end))
            name = re.sub(pattern, "", sequence.title)

        else:
            chrom, start, end, strand = sequence.title, 0, 0, "+"
            name = sequence.title

        for motif in motifs:
            for match in re.finditer(IUPAC2Regex(motif), sequence.sequence):
                
                if strand == "+":
                    match_start = start + match.start()
                    match_end = start + match.end()
                else:
                    match_end = end - (match.start() + 1)
                    match_start = end - (match.end() - 1)

                outlines.append([motif, name,
                                 "%s:%i-%i" % (chrom, match_start, match_end),
                                 strand])
                gff = GTF.Entry()
                gff.contig = chrom
                gff.start = match_start
                gff.end = match_end
                gff.feature = "motif"
                gff.source = "DREME"
                gff.strand = strand
                gff.score = "."
                gff.frame = "."
                gff.addAttribute("name", name)
                gff.addAttribute("motif", motif)
                outgffs.append(gff)

    gff_name = os.path.basename(outtable)
    PUtils.write(outtable, outlines,
                 header=["motif", "sequence", "location", "strand"])
    outgffs = map(str, outgffs)
    PUtils.write(gfffile, [[gffline] for gffline in outgffs],
                 header=["track name='%s' description='%s'" % (gff_name,gff_name)])


@cluster_runnable
def runGOSeq(genes, exprs, outfile, pwf_plot=None):
    '''Each of the params :param:genes and :param:exprs should be pandas
    Series with gene names as the index. :param:`genes` should be a 1 or 0
    indicator variable giving the positive genes and :param:`exprs` gives
    the expression level. Gene_ids should be ENSEMBL. Set pwf_plot to
    save the pwf fit plot as png'''

    import rpy2
    import rpy2.robjects as ro
    from rpy2.robjects import r as R
    from rpy2.robjects import pandas2ri
    from rpy2.robjects.packages import importr
    pandas2ri.activate()

    goseq = importr("goseq")

    genesv = ro.Vector(genes.values)
    genesv.names = ro.Vector(genes.index.values)

    exprs = exprs.fillna(0)

    exprsv = ro.Vector(exprs.values + 0.1)
    exprsv.names = ro.Vector(exprs.index.values)
    exprsv = R.rank(exprsv, ties_method="first")
 

    pwf = goseq.nullp(genesv, bias_data=exprsv, plot_fit=False)

    if pwf_plot:
        R.png(pwf_plot)
        goseq.plotPWF(pwf)
        R["dev.off"]()

    GO_analysis = goseq.goseq(pwf, "hg19", "ensGene")

    GO_analysis = R["data.frame"](GO_analysis,
                                  over_qvalue=R("p.adjust")(
                                      GO_analysis.rx2("over_represented_pvalue"),
                                      method="BH"))

    GO_analysis = R["data.frame"](GO_analysis,
                                  under_qvalue=R("p.adjust")(
                                      GO_analysis.rx2("under_represented_pvalue"),
                                      method="BH"))

    R["write.table"](GO_analysis, file=outfile, quote=False, sep="\t", row_names=False)

@cluster_runnable
def tRNABaseCounts(gtf_file, bam_file, outfile):

    import pandas

    outs = []
    for tRNA in GTF.gene_iterator(GTF.iterator(IOTools.openFile(gtf_file))):
        bamfile = pysam.AlignmentFile(bam_file, "rb")
        for transcript in tRNA:
            exons = GTF.asRanges(transcript, "exon")
            counts = iCLIP.count_intervals(bamfile,
                                           exons,
                                           strand=transcript[0].strand,
                                           contig=transcript[0].contig)
            converter = iCLIP.TranscriptCoordInterconverter(transcript)
            counts.index = converter.genome2transcript(counts.index.values)
            if len(counts) == 0:
                counts = pandas.Series([0], index=[1])
            counts.name = "count"
            counts.index.name = "base"
            counts = counts.sort_index()
            counts = counts.reset_index()
            counts["tRNA"] = transcript[0].transcript_id
            outs.append(counts)

    outs = pandas.concat(outs)

    outs.to_csv(IOTools.openFile(outfile, "w"), sep="\t", index=False)


def get3UTR(gtffile, outfile):

    outlines = []

    for transcript in GTF.transcript_iterator(GTF.iterator(IOTools.openFile(gtffile))):
        exons = GTF.asRanges(transcript, "exon")
        cds = GTF.asRanges(transcript, "CDS")

        utrs = Intervals.truncate(exons,cds)

        if transcript[0].strand == "+":
            utr3 = [exon for exon in utrs
                    if exon[0] >= cds[-1][1]]
        else:
            utr3 = [exon for exon in utrs
                    if exon[-1] <= cds[0][0]]

        for exon in utr3:
            bed = Bed.Entry()
            bed.contig = transcript[0].contig
            bed.start = exon[0]
            bed.end = exon[1]
            bed.fields = [transcript[0].transcript_id,
                          ".",
                          transcript[0].strand]

            outlines.append(str(bed))

    with IOTools.openFile(outfile, "w") as outf:
        outf.write("\n".join(outlines) + "\n")

        
def extendBedIntervals(infile, outfile, halfwidth):
    '''Get a window of a specified size around the center of each entry'''

    with IOTools.openFile(outfile, "w") as outf:
        for bed in Bed.iterator(IOTools.openFile(infile)):
            center = (bed.end-bed.start)/2
            bed.start = center - halfwidth
            bed.end = center + halfwidth
            outf.write(str(bed) + "\n")


def calculateSplicingIndex(bamfile, gtffile, outfile):

    bamfile = pysam.AlignmentFile(bamfile)

    counts = E.Counter()

    for transcript in GTF.transcript_iterator(
            GTF.iterator(IOTools.openFile(gtffile))):

        exons = GTF.asRanges(transcript, "exon")
        E.debug("Transcript: %s, %i introns" %
                (transcript[0].transcript_id, len(exons)-1))
        ei_juncs = [exon[1] for exon in exons[:-1]]
        ie_juncs = [exon[0] for exon in exons[1:]]

        for junc in ei_juncs:
            reads = bamfile.fetch(
                reference=transcript[0].contig, start=junc, end=junc+1)
            spliced = [read for read in reads if 'N' in read.cigarstring]
            unspliced = [read for read in reads if 'N' not in read.cigarstring]

            if transcript[0].stand == "+":
                direction = "ei"
            else:
                direction = "ie"

            for read in unspliced:
                if (read.reference_end >= junc+3
                   and read.reference_start <= junc-3):
                    counts[direction+"_included"] += 1
                else:
                    counts["uncounted"] += 1

            for read in spliced:
                block_ends = [block[1] for block in read.get_blocks]
                if read.reference_start <= junc-3 and junc in block_ends:
                    counts[direction+"_excluded"] += 1

        for junc in ie_juncs:

            reads = bamfile.fetch(
                reference=transcript[0].contig, start=junc-1, end=junc)
            spliced = [read for read in reads if 'N' in read.cigarstring]
            unspliced = [read for read in reads if 'N' not in read.cigarstring]

            if transcript[0].stand == "-":
                direction = "ei"
            else:
                direction = "ie"

            for read in unspliced:
                if (read.reference_end >= junc+3
                   and read.reference_start <= junc-3):
                    counts[direction+"_included"] += 1

            for read in spliced:
                block_starts = [block[0] for block in read.get_blocks]
                if read.reference_start <= junc-3 and junc in block_starts:
                    counts[direction+"_excluded"] += 1

    header = "\t".join(["exon_intron_included",
                        "exon_intron_excluded",
                        "intron_exon_included",
                        "intron_exon_excluded",
                        "uncounted"])

    with IOTools.openFile(outfile, "w") as outf:

        outf.write(header+"\n")
        outf.write("\t".join(counts["ei_included"],
                             counts["ei_excluded"],
                             counts["ie_included"],
                             counts["ie_excluded"],
                             counts["uncounted"]) + "\n")

@cluster_runnable      
def exonBoundaryProfiles(bamfile, gtffile, outfile):

    bamfile = pysam.AlignmentFile(bamfile)

    counts_collector = []
    nExamined = 0
    nEligable = 0

    E.info("Processing transcripts..")
    for transcript in GTF.transcript_iterator(
            GTF.iterator(IOTools.openFile(gtffile))):
        
        nExamined += len(transcript) - 1
        E.debug("Processing transcript %s" % transcript[0].transcript_id)

        exons = [(x.start, x.end) for x in transcript if x.feature == "exon"]
        exons.sort()


        E.debug("Processing transcript %s on contig %s, exons %s"
                % (transcript[0].transcript_id,
                   transcript[0].contig,
                   exons))
        counts = iCLIP.count_intervals(bamfile, exons, transcript[0].contig,
                                       transcript[0].strand)

        exons = exons[1:-1]
        coords_translator = iCLIP.TranscriptCoordInterconverter(transcript)
        
        counts.index = coords_translator.genome2transcript(counts.index.values)

        def elen(e):
            return e[1] - e[0]

        exons_starts = []

        for i, exon in enumerate(exons[1:]):
            if elen(exons[i-1]) > 100 and elen(exon) > 100:
                exons_starts.append(exon[0])

        exons_starts = coords_translator.genome2transcript(exons_starts)

        E.debug("%i of %i boundaries eligible, %s total counts" %
                (len(exons_starts), len(transcript)-1, counts.sum()))
        
        nEligable += len(exons_starts)
        
        for boundary in exons_starts:
            boundary_counts = counts[boundary-100:boundary+100]
            boundary_counts.index = boundary_counts.index.values - boundary

            counts_collector.append(boundary_counts)

    E.info("Finished reading transcripts. Constructing matrix")

    final_matrix = pd.concat(counts_collector, axis=1).transpose()
    final_matrix = final_matrix.fillna(0)

    E.info("Normalising and computing profile")
    row_sums = final_matrix.sum(axis=1)
    normed_matrix = final_matrix.div(row_sums.astype("float"), axis=0)
    combined = normed_matrix.sum().reset_index()

    E.info("Examined %i boundaries, of which %i were eligable and contained %i reads" %
           (nExamined, nEligable, row_sums.sum()))
    E.info("Writing Results")
    combined.to_csv(IOTools.openFile(outfile, "w"), sep="\t", index=False, header=["position", "density"])


def findNuclearLocalisation(infile, outfile):

    from rpy2.robjects import r as R, Formula
    from rpy2.robjects.packages import importr

    deseq = importr("DESeq2")

    c = R.c

    counts = R('read.delim("%(infile)s",sep="\t", row.names=1)' % locals())

    counts = R["as.matrix"](counts)
    col_data = R.strsplit(R.colnames(counts), "_")
    col_data = R["do.call"](R.rbind, col_data)
    col_data = R["data.frame"](col_data)
    col_data.rownames = R.colnames(counts)
    col_data.names = c("knockdown", "fraction", "replicate")

    print col_data
    keep = col_data.rx((col_data.rx2("fraction").ro != "Total").ro
                       & (col_data.rx2("knockdown").ro == "Control"),
                       True)

    print keep

    kept_counts = counts.rx(True, R.rownames(keep))
    print R.relevel(keep.rx2("fraction"), "Cytoplasmic")
    keep.rx[True,"fraction"] = R.relevel(keep.rx2("fraction"), "Cytoplasmic")
   
    fraction_ds = deseq.DESeqDataSetFromMatrix(
        kept_counts, keep, Formula("~ replicate + fraction"))
    fraction_ds = deseq.DESeq(fraction_ds)
    fraction_results = deseq.results(fraction_ds, independentFiltering=False,
                                     addMLE=True)

    fraction_results = R("as.data.frame")(fraction_results)
    fraction_results = R("data.frame")(fraction_results,
                                       Gene_id=R.rownames(fraction_results))

    R["write.table"](fraction_results, outfile, quote=False,
                     sep="\t", row_names=False)


def findhnRNPUDependentGenes(connection, outfile):

    from rpy2 import robjects as ro
    py2ri_old = ro.conversion.py2ri
 #   ro.conversion.py2ri = ro.numpy2ri

    import pandas.rpy.common as com

#    ro.numpy2ri.activate()

    counts = PUtils.fetch_DataFrame(''' SELECT DISTINCT gene_id,
                                              transcript,
                                              WT_EstimatedNumReads as WT,
                                              hnRNPU1kd_EstimatedNumReads as kd
                                         FROM fuRNAseq as rna
                                         INNER JOIN biotypes
                                           ON biotypes.transcript_id = rna.transcript ''',
                                    connection)

    counts = counts.drop("Transcript", axis=1)
    counts = counts.groupby("gene_id").sum()
    counts.WT = counts.WT.astype(int)
    counts.kd = counts.kd.astype(int)

#    counts_r = ro.r.matrix(counts.as_matrix())
    counts_r = com.convert_to_r_matrix(counts)
    ro.r.assign("counts_r", counts_r)
    ro.numpy2ri.deactivate()
    ro.conversion.py2ri = py2ri_old

    ro.r.assign("rn", ro.StrVector(list(counts.index.values)))
    ro.r.assign("cn", ro.StrVector(list(counts.columns.values)))
    ro.r("rownames(counts_r) <- rn")
    #counts_r.colnames = ro.StrVector(list(counts.index.values))
    ro.r("colnames(counts_r) <- cn")
    
    counts_r = ro.r("counts_r")

    col_data = ro.r("data.frame")(si=ro.r("c(colnames(counts_r))"))
    print ro.r.levels(col_data.rx2("si"))
    col_data[0] = ro.r.relevel(col_data.rx2("si"), "WT")
    print ro.r.relevel(col_data.rx2("si"),"WT")
    print ro.r.levels(col_data.rx2("si"))

    deseq = ro.packages.importr("DESeq2")
    si_ds = deseq.DESeqDataSetFromMatrix(counts_r, col_data, ro.Formula("~si"))
    si_ds = deseq.DESeq(si_ds)
    si_results = deseq.results(si_ds, independentFiltering=False, addMLE=True)
    print (ro.r.head(si_results))
    si_results = ro.r("as.data.frame")(si_results)
    si_results = ro.r("data.frame")(si_results, gene_id=si_results.rownames)

    ro.r("write.table")(si_results, outfile, quote=False, sep="\t",
                        row_names=False)


def mergeExonsAndIntrons(exons, introns):
    ''' Exons are merged with all other exons and introns with all
    other introns. Introns and exons are then combined such that
    each non-overlapping exon and intron is output as a seperate
    GTF exon. Where exons and introns overlap, three seperate
    exons are output one for the unique parts of each exon
    and one for the overlap. '''

    template_entry = exons[0]
    try:
        exons = [(start, end, "exon") for start, end
                 in GTF.asRanges(exons, "exon")]
    except AttributeError:
        exons = [(start, end, "exon") for start, end
                 in Intervals.combine(exons)]

    try:
        introns = [(start, end, "intron") for start, end
                   in GTF.asRanges(introns, "exon")]
    except AttributeError:
        introns = [(start, end, "intron") for start, end
                   in Intervals.combine(introns)]

    combined_exons = exons + introns
    combined_exons.sort()
    
    new_exons = []
    last_from, last_to, last_feature = combined_exons[0]
    
    for this_from, this_to, this_feature in combined_exons[1:]:

        if this_from >= last_to:
            new_exons.append((last_from, last_to, last_feature))
            last_from, last_to, last_feature = this_from, this_to, this_feature
            continue

        new_exons.append((last_from, this_from, last_feature))
            
        if this_to <= last_to:
            new_exons.append((this_from, this_to, this_feature))
            last_from = this_to

        else:
            new_exons.append((this_from, last_to, "exon"))
            last_feature = this_feature
            last_from = last_to
            last_to = this_to
    
    entry = GTF.Entry()

    try:
        entry = entry.copy(template_entry)
    except AttributeError:
        pass

    entry.feature = "exon"
    entry.transcript_id = entry.gene_id
    entry.source = "merged"
    iexon = iintron = 1

    for start, end, feature in new_exons:

        entry.start = start
        entry.end = end
        if feature == "exon":
            entry.attributes["exon_id"] = "E%03d" % iexon
            iexon += 1
        else:
            entry.attributes["exon_id"] = "I%03d" % iintron
            iintron += 1

        yield entry


def getTranscriptsPlusRetainedIntrons(infile, outfile):
    ''' Look for transcripts with retained introns and the
    equivalent transcript without a retained intron. Output
    a merged gene model, where the retained intron is a seperate
    exon. Also merge in the detained introns '''

    outf = IOTools.openFile(outfile, "w")

    for gene in GTF.gene_iterator(
            GTF.iterator(IOTools.openFile(infile))):
        
        gene_out = []
        introns_out = []

        # now find if any of the transcripts are retained intron
        # versions of any of the others
        for first, second in itertools.product(gene, gene):
            
            first = sorted([entry for entry in first
                            if entry.feature == "exon"],
                           key=lambda x: x.start)
            second = sorted([entry for entry in second
                             if entry.feature == "exon"],
                            key=lambda x: x.start)

            first_introns = set(GTF.toIntronIntervals(first))
            second_introns = set(GTF.toIntronIntervals(second))
            
            if len(first_introns-second_introns) > 0 and \
               len(second_introns-first_introns) == 0:
                novel_introns = list(first_introns-second_introns)

                def _filterIntron(intron):
                    return intron[0] > second[0].start and \
                        intron[1] < second[-1].end

                novel_introns = filter(_filterIntron, novel_introns)

                if len(novel_introns) > 0:
                    gene_out.extend(first)

                for intron in novel_introns:
                    introns_out.append(intron)

        if len(gene_out) == 0:
            continue

        for gff in mergeExonsAndIntrons(gene_out, introns_out):
            outf.write("%s\n" % gff)


def insertDetainedIntronsIntoTranscripts(transcripts, introns, outfile):
    ''' This function takes the annotated detained introns of sharp
    and attempts to find the transcript from which they came, and
    returns a flattened gene containing combined exons from the
    transcripts containing the intron, plus an exon containing the
    intron'''

    outf = IOTools.openFile(outfile, "w")

    E.debug("Reading and Indexing bedfile")
    beds = Bed.readAndIndex(IOTools.openFile(introns), with_values=True)

    for gene in GTF.gene_iterator(
            GTF.iterator(IOTools.openFile(transcripts))):

        # Find any detained introns that are in the full interval
        # of the gene
        gene_start = min(exon.start
                         for transcript in gene
                         for exon in transcript)
        gene_end = max(exon.end for transcript in gene for exon in transcript)
        try:
            candidate_beds = set((start, end)
                                 for start, end, bed
                                 in beds[gene[0][0].contig].find(
                                     gene_start, gene_end)
                                 if bed.strand == gene[0][0].strand)
        except KeyError:
            candidate_beds = set()
         
        gene_out = []
        introns_out = []
        # First find if any transcripts have 'detained introns' and
        # add them
        for transcript in gene:
            introns = set(GTF.toIntronIntervals(transcript))
            retained_beds = candidate_beds & introns
        
            if len(retained_beds) > 0:
                gene_out.extend(exon for exon in
                                transcript if exon.feature == "exon")

            for intron in retained_beds:
                introns_out.append((intron[0], intron[1]))

        introns_not_found = set(candidate_beds) - set(introns_out)
        if len(introns_not_found) > 0:
            # exact homes not found. Find approximate homes.

            for transcript in gene:
                exons = GTF.asRanges(transcript, ("exon"))
                starts, ends = zip(*exons)
                for intron in introns_not_found:

                    if Intervals.calculateOverlap(exons, [intron]) == 0 \
                       and (intron[0] in ends or intron[1] in starts):
                        gene_out.extend(transcript)
                        introns_out.append(intron)

        introns_not_found = set(candidate_beds) - set(introns_out)

        if len(introns_not_found) > 0:
            E.warn("Homes not found for %s in gene %s chr=%s start=%i, end=%i"
                   % (introns_not_found, gene[0][0].gene_id, gene[0][0].contig,
                      gene_start, gene_end))
            
        if len(introns_out) == 0:
            continue

        for gff in mergeExonsAndIntrons(gene_out, introns_out):
            outf.write("%s\n" % str(gff))

def mergeDetainedAndRetainedIntrons(infile, outfile):

    outf = IOTools.openFile(outfile, "w")

    for gene in GTF.flat_gene_iterator(GTF.iterator(
            IOTools.openFile(infile))):
        
        exons = [exon for exon in gene
                 if "E" in exon.asDict()["exon_id"]]

        introns = [exon for exon in gene
                   if "I" in exon.asDict()["exon_id"]]

        for gff in mergeExonsAndIntrons(exons, introns):

            outf.write("%s\n" % str(gff))
    
    outf.close()


def convertGenesetToTranscriptomeCoords(infile, outfile):

    with IOTools.openFile(outfile, "w") as outf:
        for transcript in GTF.transcript_iterator(
                GTF.iterator(
                    IOTools.openFile(infile))):

            converter = iCLIP.TranscriptCoordInterconverter(transcript)
            transcript.sort(key=lambda x: x.start)

            exon_intervals = converter.transcript_intervals

            for interval, entry in zip(exon_intervals, transcript):
                entry.contig = entry.transcript_id
                entry.strand = "+"
                entry.start = interval[0]
                entry.end = interval[1]
                outf.write(str(entry) + "\n")


