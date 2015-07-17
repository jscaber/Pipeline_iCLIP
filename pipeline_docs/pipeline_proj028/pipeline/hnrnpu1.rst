Correlation with hnRNPU1
===========================


hnRNPU1 metagene profile over exons, using data from :PMID:`22325991`

.. report:: hnrnpu.HnRNPUMeta
   :render: r-ggplot
   :groupby: all
   :statement: aes(x=region_bin, y=area, colour=track) + geom_line() + theme_bw() + ylab("Density") + xlab("Relative Position") + scale_x_continuous(breaks=c(0,1000), labels=c("TSS","TTS"))

   Metagene plot of depth of hnRNPU1 reads over all transcripts



Context stats.

.. report:: hnrnpu.HnRNPUContext
   :render: r-ggplot
   :groupby: all
   :statement: aes(x=track, y=alignments, fill=category) + geom_bar(stat="identity", position="fill") + coord_flip() + theme_bw() + theme(aspect.ratio=0.5)

   hnRNPU1 tags contexts


Looks like is is mostly in the introns, so perhaps need to do whole transcript metagene


.. report:: hnrnpu.HnRNPUWholeTranscriptMeta
   :render: r-ggplot
   :groupby: all
   :statement: aes(x=region_bin, y=area, colour=track) + geom_line() + theme_bw() + ylab("Density") + xlab("Relative Position") + scale_x_continuous(breaks=c(0,1000), labels=c("TSS","TTS"))

   Metagene plot of depth of hnRNPU1 reads over both introns and exons


Effect of knockdown on nuclear localisation
---------------------------------------------

Only genes with an avearge of over 50 reads per sample in both the FuRNAseq and the stubbs nuclear measurements are included.


.. report:: hnrnpu.KDVsNuclear
   :render: r-ggplot
   :groupby: all
   :statement: aes(y=log2(KD), x=nuclear) + geom_point(alpha=0.25, size=1) + theme_bw() +  xlab("log2 fold nuclear/cytoplasmic") + ylab("Fold change on hnRNPU1 knockdown") + geom_smooth(method="lm")

   Comparing response to kd to nuclear localistation


.. report:: hnrnpu.KDVsNuclear
   :render: r-ggplot
   :groupby: all
   :statement: aes(y=log2(KD), x=nuclear > 2) + geom_point(position=position_jitter(w=0.1,h=0), size=1) + geom_boxplot(fill=NA) + theme(legend.position="bottom") + theme_bw() +  xlab("Nuclear localised") + ylab("Fold change on hnRNPU1 knockdown")

   Comparing response to kd to nuclear localistation (log2(nuclear signal/cytoplasmic signal) > 2)


.. report:: hnrnpu.KDVsNuclearLinc
   :render: r-ggplot
   :groupby: all
   :statement: aes(y=log2(KD), x=nuclear) + geom_point(alpha=0.25, size=1) + theme_bw() +  xlab("log2 fold nuclear/cytoplasmic") + ylab("Fold change on hnRNPU1 knockdown") + geom_smooth(method="lm")

   Comparing response to kd to nuclear localistation for lincRNAs


.. report:: hnrnpu.KDVsNuclearLinc
   :render: r-ggplot
   :groupby: all
   :statement: aes(y=log2(KD), x=nuclear > 2) + geom_point(position=position_jitter(w=0.1,h=0), size=1) + geom_boxplot(fill=NA) + theme(legend.position="bottom") + theme_bw() +  xlab("Nuclear localised") + ylab("Fold change on hnRNPU1 knockdown")

   Comparing response to kd to nuclear localistation (log2(nuclear signal/cytoplasmic signal) > 2) for lincRNAs


.. report:: hnrnpu.KDVsNuclearLinc
   :render: table
   :transform: filter
   :groupby: slice
   :slices: Nuclear
   :tf-fields: symbol,nuclear,KD

   Table of nuclear localised LincRNAs and expression responses to hnRNPU1 knockdown. 

