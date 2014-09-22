.. _saturation:

Saturation Analysis
=====================

There are only a limited number of distinct molecules in library. As we sequence more and more of a library, we will have more and more of the possible different molecules and a higher proportion of those we sequence will be duplicates of things we have already sequenced. Thus, the library becomes 'saturated'. We can monitor this saturation by looking at the rate at which we discover new unique sequences as we do more sequencing. To do this we select random subsets of reads of different sizes from each library and ask how many unique sequences are present:

.. report:: Sample_QC.AlignmentSaturation
   :render: r-ggplot
   :groupby: all
   :statement: aes(x=subset, y=counts, color = factor, shape = factor) + geom_point() + geom_line() + facet_wrap(~replicate) + theme_bw(base_size=18) + theme(aspect.ratio = 1) + xlab("Fraction Sampled") + ylab("Unique Read Count")

   Subsampling of alignments

We can firstly see how many more unique sequences are present in replicates 2 and 3 compared to replicate 1. Secondly we can see that these libraries havn't yet reached saturation, but that they are starting to in some cases.

To calculate how saturated each of these libraries is we first need to estimate how many unique sequences there are present in library. That is work out where on the y axis of the plots about the curves will saturate. If we select each read from the original pools at random, then the saturation curve should follow the equation

.. math:: U = n(1-(1-\frac{1}{n})^S)

where U is the number of unique sequences identified, S is the total number of sequences obtained and n is the number of total number of unique sequences in the library. If we fit this curve to the data we should be able to estimate n. However, when we do this, we find that the fits are not very good:

.. report:: Sample_QC.LibrarySize_Binom
   :render: r-ggplot
   :statement: aes(x=subset, y=alignments) + geom_point() + geom_line(aes(y=expected_unique)) + geom_hline(yintercept=rframe$library_size[1]) + theme_bw()
   :layout: column-4
   :tracks: Chtop-FLAG-R2
   
   Curve fits for saturation using Binomal distribution. Solid line indicates estimate of library size.


This suggests that something is wrong with our model. None the less, we can try to fit a more general equation for a saturating curve:

.. math:: U = \frac{n}{k + S}


Here and additional parameter is fit in addition to n. This should, therefore fit a wider range of curves. Indeed the fits are much better, but still not perfect. 

.. report:: Sample_QC.LibrarySize_mm
   :render: r-ggplot
   :statement: aes(x=subset, y=alignments) + geom_point() + geom_line(aes(y=expected_unique)) + geom_hline(yintercept=rframe$library_size[1]) + theme_bw()
   :tracks: Chtop-FLAG-R2
   :layout: column-4

   curve fits for saturation using reciprical fit. Solid line indicates estimate of library size

These problems with fit are probably related to non-random sequencing of the original reads and connected to the problems with the UMIs outlined in :ref:`mapping`. This would probably lead to an under-estimate of the total library size and the percent saturated, but may still be useful for comparing libraries. The table below presents the estimated complete library sizes and the percent saturation of each of our samples.

.. report:: Sample_QC.mm_fit_stats
   :render: table

   Library size estimates
