from __future__ import division
import pandas as pd, numpy as np, networkx as nx, time
from scipy.sparse import dok_matrix
from scipy.sparse import identity
from scipy.sparse import diags
from numpy.linalg import inv
from numpy import square
from numpy import trace
from numpy import amax
from math import sqrt

class Similarity:

    def __init__(self, g1, g2):
        self.R = nx.DiGraph()
        self.R.add_nodes_from(g1)
        self.R.add_nodes_from(g2)
        self.R1 = nx.DiGraph()
        self.R1.add_nodes_from(self.R)
        self.R1.add_edges_from(g1.edges())
        self.R2 = nx.DiGraph()
        self.R2.add_nodes_from(self.R)
        self.R2.add_edges_from(g2.edges())
        A1 = nx.adjacency_matrix(self.R1)
        A2 = nx.adjacency_matrix(self.R2)
        self.result = self.run(A1, A2)

    def InverseMatrix(self, A):
        I = identity(A.shape[0])
        D = diags(sum(A).toarray(), [0])
        c1 = trace(D.toarray()) + 2
        c2 = trace(square(D).toarray()) - 1
        h_h = sqrt((-c1 + sqrt(c1 * c1 + 4 * c2)) / (8 * c2))
        a = 4 * h_h * h_h / (1 - 4 * h_h * h_h)
        c = 2 * h_h / (1 - 4 * h_h * h_h)
        M = c * A - a * D
        S = I
        mat = M
        power = 1
        while amax(M.toarray()) > 1e-09:
            if power < 7:
                S = S + mat
                mat = mat * M
                power += 1

        return S

    def run(self, A1, A2):
        S1 = self.InverseMatrix(A1)
        S2 = self.InverseMatrix(A2)
        d = 0
        for i in range(A1.shape[0]):
            for j in range(A1.shape[0]):
                d += (sqrt(S1[(i, j)]) - sqrt(S2[(i, j)])) ** 2

        d = sqrt(d)
        sim = 1 / (1 + d)
        return 1 - sim