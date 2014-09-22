.. _mapping:

Read Processing and mapping
============================

There are many stages in the conversion of raw reads into mapped cross linked sites, and the success of this stages is perhaps the most critical for all downstream analysis. For this experiment the process was as follows:

::

    Screen for PhiX     Remove primer/adaptor       Qualtiy     Map reads       Remove putative
       Sequence     -->     sequence and       -->  control -->    to      -->       PCR
                         demultiplex reads                       genome           duplicates


At each step here reads can be lost and/or problems can show up. The plots below show how many reads we got for each sample after taking each read and assigning it to a sample and how many reads are in the final, output files at the end for each file.

.. report:: Sample_QC.ReadsPerSample
   :render: r-ggplot
   :statement: aes(y=total, x=sample) + geom_bar(stat="identity") + theme_bw() + theme(axis.text.x = element_text(angle=90)) + scale_y_continuous(labels = function(x,...) format(x,...,big.mark=",", scientific= F, trim = T)) + ylab("Reads")

   Number of reads for each sample

.. report:: Sample_QC.FinalReads
   :render: r-ggplot
   :statement: aes(y=reads_mapped, x=sample) + geom_bar(stat="identity") + theme_bw() + theme(axis.text.x = element_text(angle=90)) + scale_y_continuous(labels = function(x,...) format(x,...,big.mark=",", scientific= F, trim = T)) + ylab("Total unique mapped reads")

   Final total mapped reads

Notice that we start with substainlly fewer reads in replicate 1 and in the Nxf1 and FlipIn samples, but that the disbalance is even worst by the time that we get to the output. Most reads are successfully demultiplexed, adaptor trimmed and mapped. The difference between the samples is mostly explained by the percentage of reads that are PCR duplicates in those files. The following plot shows the percentage of mapped reads that are left in each sample after removing those that look like PCR duplicates:

.. report:: Sample_QC.PercentDeDuped
   :render: r-ggplot
   :statement: aes(y=p_unique * 100, x=sample) + geom_bar(stat="identity") + theme_bw() + theme(axis.text.x = element_text(angle=90)) + scale_y_continuous(labels = function(x) sprintf("%.0f%%",x)) + ylab("Percent reads unique")

   Percent of Reads Unique

The original pipeline described in the iCLIP papers used a program for mapping which does not allow for reads to cross exon/exon boundaries (they most map to a contigous section of the genome). This assumes that the factors in question will map to the primary RNA transcript rather than the processed mRNA, but we don't know if this is the case for the factors we are interested in. Thus here I have used a program that allows mapping to either the processed mRNA or the primary transcript. The fraction of reads which are split across exon/exon bounardies will give us a sense of whether reads are mapping to mRNA or primary RNA.

.. report:: Sample_QC.PercentSpliced
   :render: r-ggplot
   :statement: aes(Track, pspliced) + geom_bar(stat="identity") +  scale_y_continuous(labels = function(x) sprintf("%.0f%%",x*100)) + ylab("Percent reads spliced") + theme_bw() + theme(axis.text.x=element_text(angle=90))

   Percent of deduped reads spliced

As we can see above, a non-trival fraction of reads, particularly for Alyref cross the intron exon boundary. For comparison, in a good RNA-seq experiment, around 15% of reads are spliced. This suggests that, for Alyref at least, we are sequencing mature mRNA rather than primary transcript. This is also suppored by context of mapping (see :ref:`mappingcontext`).

Analysis of UMI frequency
--------------------------

The design of the experiment includes the use of short random sequences in the primers. These are known as unique molecular identifiers or UMIs. Many next generation library preparation techniques use PCR to amplify a small amount of starting material up to be enough to sequence. When we measure the abundance of something by the number of reads in an NGS experiment, we are making the assuption that the number of reads after PCR is proportional to the abundance before PCR. This is problematic if the amplification of particular sequences is bias in some way, which, with PCR and many NGS techniques we know it is. In experiments where there are a large number of possible reads, we assume that the probablility two identical reads being PCR duplicates is high compared to the probability that they represent two distinct molecules from the pre-PCR pool, and thus count the number of unique reads (actaully the number of unique read mapping locations). However, where the mapping positions are restricted, this no longer holds and two identifcal reads may well represent distinct events from the pre-PCR pool. UMIs help us here by adding random sequences to fragments before PCR and thus reducing the chance of two reads being identical unless they are PCR duplicates.

For this to work, we rely on the UMI that is ligated to each fragment being random, and thus the chance of two different fragements of identical sequence ligating to the same UMI being low. If the selection of UMI is random then the frequency with which each UMI is used should be similar and should follow a Binomial distribution. 

.. math:: frequency(UMI_i) \sim B(\frac{1}{4^l}, n)

where l is the number of bases in the UMI and n is the number of biologically unique fragments sequenced. As n gets large (and it is very large here), the distribution of UMI freqencies should be approximately normal. As we can see below, this is unfortunately not the case:

.. report:: Sample_QC.DedupedUMIStats
   :render: r-ggplot
   :statement: aes(Count) +facet_grid(replicate~Factor) + stat_density() + coord_cartesian(xlim=c(0,500)) + theme_bw()

   Distribution of UMI frequencies


Indeed if we look at the same thing on a log scale, we can see that the distribution is actaully more like log-normal:

.. report:: Sample_QC.DedupedUMIStats
   :render: r-ggplot
   :statement: aes(Count) +facet_grid(replicate~Factor) + stat_density() + scale_x_log10() + theme_bw()

   Distribution of UMI frequencies (log scale)


However, more rigurous testing will be neccesary to test this formally. 



