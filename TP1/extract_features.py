# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function

import numpy
import pandas
import sys

from argparse import ArgumentParser

def parse_args():
    parser = ArgumentParser(
        description = 'Extract header features from CSV file with mail data',
    )
    parser.add_argument('-c', '--column_file', type = file, help = 'File with final column list.')
    args = parser.parse_args()

    if args.column_file:
        args.columns = pandas.Index(map(str.strip, args.column_file.readlines()))
    else:
        args.columns = None

    return args

# Extrae cierto conjunto de features aplicado individualmente a ciertas columnas.
class ExtractedFeature(object):
    """
    name -- Nombre del feature. La columna final queda como col_name.
    trans -- Función que se le aplica a ciertas columnas para conseguir el feature.
    filt -- Nombre de columna, lista de columnas, o función (columna -> booleano)
        que decide a qué columnas se le aplica.
    filna -- Con qué rellenar NaNs.
    """
    def __init__(self, name, trans, fillna = numpy.nan, filt = None):
        self.name = name
        self.trans = trans
        self.fillna = fillna

        self.filt = pandas.Index([filt] if type(filt) == str else filt) if filt else None

    # Usa el extractor para extraer datos de un DataFrame.
    def extractFrom(self, table):
        if self.filt is None:
            cols = table.columns
        else:
            cols = table.columns & self.filt
        
        return (
            table[cols].apply(lambda x: self.trans(x.dropna()))
            .rename(columns = lambda x: x + '_' + self.name)
            .fillna(self.fillna, downcast = 'infer')
        )

def avglen(s):
    return (s.str.strip().str.len() + 1).sum() / (s.size + 1)

def avg1p(s):
    return sum(1 + x for x in s) / (len(s) + 1)

# Extrae muchos datos de una tabla.
def extractAll(table):
    sep = ','
    features = [
        ExtractedFeature('length', lambda x: x.str.len(), 0),

        ExtractedFeature('fields', lambda x: x.str.count(sep) + 1, 0),
        ExtractedFeature('words', lambda x: x.str.strip().str.count(' ') + 1, 0),

        ExtractedFeature('avgFieldLength', lambda x: x.str.split(sep).apply(lambda x: avg1p(map(lambda x: len(x.strip()), x))), 0),
        ExtractedFeature('avgWordLength', lambda x: x.str.split(' |<NL>').apply(lambda x: avg1p(map(lambda x: len(x.strip()), x))), 0),

        ExtractedFeature('exists', lambda x: x.notnull(), False),
    ]

    return pandas.concat(map(lambda x: x.extractFrom(table), features), axis = 1)

def main():
    args = parse_args()

    debug_file = 'data/train_sample.csv'
    train = pandas.read_csv(
        sys.stdin,
        encoding = 'utf-8',
        chunksize = 25000,
        dtype = object,
        index_col = 'num'
    )

    first = True
    for e, chunk in enumerate(train):
        print('Parsing chunk {}'.format(e), file = sys.stderr)

        if 'spam' in chunk.columns:
            features = extractAll(chunk.drop('spam', axis = 1))
            features['spam'] = chunk['spam']
        else:
            features = extractAll(chunk)

        # Ugly hack: if b : Bool, b * 1 : Int
        (features.reindex(columns = args.columns, fill_value = 0) * 1).to_csv(sys.stdout, index = True, header = first)
        first = False

if __name__ == '__main__':
    main()
