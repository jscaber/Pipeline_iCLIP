.. _fragsizeanal:

Fragment Size distribution
---------------------------

During the library preparation protocol, the library is divided into three size fragments, which are then processed seperately to prevent bias'. At the end of the protocol, these three size fragments were recombined at a ratio of 5:5:1. To examine if this was the correct ratio to recombine the pools at I have analysed the distribution of fragment lengths in the data.

Examining the gel images of the samples that produced the libraries, I estimate that the three bands are about 45-75, 75-120 and 120-200 after the removal of primer sequence. I have estimated the fraction of reads that fall into each of these size categories (plus the ones that are smaller), for each library:

.. report:: Sample_QC.MappedFragLength
   :render: r-ggplot
   :transform: melt
   :statement: aes(x=Track, y=Data/sum(Data), fill=Slice) + geom_bar(position="fill", stat="identity") + ylab("Fraction of reads") + scale_fill_discrete(name="Length bin (bp)") + coord_flip() + theme_bw()

   Distribution of fragment sizes of the raw reads mapped on the genome

You can see that in each case the largest bin is the smallest, those fragments 45-85bp long. A slose second in most cases is those that are even smaller that the smallest band on the the gel - those 0-45. After that come the 85-120 bins and the 120+ bins are mostly tiny. 

This bias could be due to over amplification of the smaller fragments, meaning that although they represent a larger proportion of the data sequenced, they do not provide more infomation. To look at this, we can examine the same data produced after the PCR duplicates have been removed:

.. report:: Sample_QC.DedupedFragLengths
   :render: r-ggplot
   :transform: melt
   :statement: aes(x=Track, y=Data/sum(Data), fill=Slice) + geom_bar(position="fill", stat="identity") + ylab("Fraction of reads") + scale_fill_discrete(name="Length bin (bp)") + coord_flip() + theme_bw()

Here we can see that the fragements that are smaller than the supposed smallest expected fragment size make up an even larger fraction of the reads. This is confirmed by looking at the ratio of the proportions in the raw mapped reads to those in the deduplicated reads, telling us what fraction of reads in each size category are provideing unique infomation:

.. report:: Sample_QC.LengthDedupedRatios
   :render: interleaved-bar-plot
   

   Percent of reads unique after deduplication for each size category

While the numbers differ from sample to sample with can see that on average, the three expected size categories have a similar fraction of unique reads. However, the category for fragments smaller than we were expecting to see has significatly more unique reads than the other categories in every case.

