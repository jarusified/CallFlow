import time

# Lookup by the node hash
def lookup(df, node_hash):
    return df.loc[df['node'] == node_hash] 


# Get the inclusive runtime of the root
def getRunTime(gf):
    root_metrics = lookup(gf.dataframe, gf.graph.roots[0])
    return root_metrics[['CPUTIME (usec) (I)']].max()[0]

# TODO: Move to a new file if we need to filter by more attributes
def byIncTime(gf,):
    t = time.time()
    threshold = 0.01
    max_inclusive_time = getRunTime(gf)
    print max_inclusive_time*threshold
    filter_df = gf.dataframe[(gf.dataframe['CPUTIME (usec) (I)'] > threshold*max_inclusive_time)]
    print '[Filter] Removed {0} nodes by threshold {1}'.format(gf.dataframe.shape[0] - filter_df.shape[0], max_inclusive_time)
    print '[Filter] Nodes left: '.format(filter_df.shape[0])
    print "Time consumed", time.time() - t
    return filter_df



