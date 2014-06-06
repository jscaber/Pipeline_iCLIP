.. _reproducibility:

Reproducibility analysis
=========================

Sugimoto et al defined a metric which they called "reproducibility". This the number of cross-link sites in sample A that are reproduced in either one other replicate (1-fold replication) or both other replicates(2-fold replication). We can do this for bases in sample A that have 1, 2 or more reads mapping to them (level). For example, both the cross linked bases in sample A below on the left, denoted by the X, are reproduced 1-fold, where as on the right the replication is two fold:

::

                       1-fold reprodution                              2-fold reproduction
                           X            X                                X
    Sample A: 5'-----------------------------------3'        5'-----------------------------------3'

                           X                                             X
    Sample B: 5'-----------------------------------3'        5'-----------------------------------3'
 
                                        X                                X
    Sample C: 5'-----------------------------------3'        5'-----------------------------------3'



Below the level 1 replication is 50%, while the level 2 replication is 100%:


::
                                        

                           X
                           X            X                  
    Sample A: 5'-----------------------------------3'      

                           X                               
    Sample B: 5'-----------------------------------3'      
 
                                                          
    Sample C: 5'-----------------------------------3'      



The 1 and 2 fold reproducibilities grouped by factor are resented below, with 1-fold reproducilibity on the left, and 2-fold on the right. 


.. report:: Sample_QC.Reproducibility
   :render: r-ggplot
   :transform: label-paths
   :statement: aes(level, reproducibility, color=Replicate) + geom_line() + geom_point() + facet_grid(Slice ~ Track) + coord_cartesian(xlim=c(0,5)) + theme_bw()
   :tf-label-level: 3

   Reproduciblity


Notice that those the larger samples seem to have a lower reproducibility. This is because, by neccessity, if there are a larger number of sites in sample A, then it is not possible for them all to reproduce. This could either mean that the extra signal is noise, or that it is real signal that would appear in the other replicates if more sequencing was performed. 


We can also look if the signal present in the Alyref, Chtop and Nxf1 samples is reproduced in the FlipIn samples to see how much of the signal is specific or non-specific.

.. report:: Sample_QC.ReproducibilityVsControl
   :render: r-ggplot
   :transform: label-paths
   :slices: 1,3
   :statement: aes(level,reproducibility,color=Replicate) + geom_line() + geom_point() + facet_grid(Slice~Track) + theme_bw() + coord_cartesian(xlim = c(0,25))
   :tf-label-level: 3

   Reproducibility vs. Controls


We can see that as we increase the depth of sequencing we are more likely to reproduce signal from the RBP in the control pull down. Below we show the ratio of the reproducibility in the RBP pull downs to the reproducibility in the control pull downs, for Alyref and Chtop, at low depths there is extra infomation present in the samples above that that is present in the control pull down. The situation is slightly worst in replicate 2, this was the replicate that had band in the control pull down gels. Note also that the situation is worst for Nxf1:

.. report:: Sample_QC.ReproducibilityReplicateVsControl
   :render: r-ggplot
   :transform: label-paths
   :statement: aes(depth,log2(ratio),color=Replicate) + geom_line() + geom_point() + facet_grid(Slice~Track) + coord_cartesian(xlim=c(0,10)) + theme_bw()
   :tf-label-level: 3
   :slices: 1


Finally we can use the reproducibility of one sample in another to produce a measure of how similar the samples are. We can use this to cluster the samples. We convert the level 1 reproducbility between every pair of samples into a similarity using the jaccard statistic:

.. math:: j = \frac{A \cap B}{A \cup B}

We then use hierachical clustering to cluster similar samples together:

 
.. report:: Sample_QC.ClusterSamplesOnReproducibility
   :render: user
   

   Samples clustered on reproducibility
 

Two very clear groups of similar samples are formed. In the first group are replicates 2 and 3 of Alyref and Chtop. In the second group are replicates 2 and 3 of Nxf1 and replicate 1 of Alyref and Chtop along with one of the replicates of the control FlipIn. A third, less distinct group contains replicate 1 of Nxf1 and another control replicate. The final control replicate sits out on its own. It is unclear at this point how much of the clustering is driven by size, so these results should be treated with some caution.


