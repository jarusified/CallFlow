import numpy as np
from scipy import stats
from scipy.stats import iqr
import math
import collections
import numpy as np

class BoxPlot:
    def __init__(self, df):
        self.q = {}
        self.q['Inclusive'] = self.quartiles(df, attr='time (inc)')
        self.q['Exclusive'] = self.quartiles(df, attr='time')
        
        self.outliers = {}
        self.outliers['Inclusive'] = self.iqr_outlier(df, attr='time (inc)', axis=0)
        self.outliers['Exclusive'] = self.iqr_outlier(df, attr='time', axis=0)

    def quartiles(self, df, attr=''):
        return np.quantile(np.array(df[attr].tolist()), [0, 0.25, 0.5, 0.75, 1.0]).tolist()

    def q1(self, x, axis = None):
        return np.percentile(x, 25, axis = axis)

    def q3(self, x, axis = None):
        return np.percentile(x, 75, axis = axis)

    def iqr_outlier(self, df, attr='', axis = None, bar = 1.5, side = 'both'):
        assert side in ['gt', 'lt', 'both'], 'Side should be `gt`, `lt` or `both`.'

        data = np.array(df[attr])
        d_iqr = iqr(data, axis = axis)
        d_q1 = self.q1(data, axis = axis)
        d_q3 = self.q3(data, axis = axis)
        iqr_distance = np.multiply(d_iqr, bar)

        stat_shape = list(data.shape)

        if isinstance(axis, collections.Iterable):
            for single_axis in axis:
                stat_shape[single_axis] = 1
        else:
            stat_shape[axis] = 1

        if side in ['gt', 'both']:
            upper_range = d_q3 + iqr_distance   
            upper_outlier = np.greater(data - upper_range.reshape(stat_shape), 0)

        if side in ['lt', 'both']:
            lower_range = d_q1 - iqr_distance
            lower_outlier = np.less(data - lower_range.reshape(stat_shape), 0)

        if side == 'gt':
            return upper_outlier.tolist()
        if side == 'lt':
            return lower_outlier.tolist()
        if side == 'both':
            return np.logical_or(upper_outlier, lower_outlier).tolist()