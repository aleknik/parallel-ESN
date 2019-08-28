import os
import random

import numpy as np
import pandas as pd
from mpi4py import MPI

from esn_parallel import ESNParallel
from mpi_logger import print_with_rank

comm = MPI.COMM_WORLD
size = comm.Get_size()
rank = comm.Get_rank()

master_node_rank = 0


def dict_to_string(dict):
    string = ''
    for index, item in enumerate(sorted(dict.items())):
        key, val = item
        if index != 0:
            string += '-'
        string += str(key) + '=' + str(val)

    return string


def standardize_data(data):
    data = data.T
    data = (data - data.mean()) / data.std()
    return data.T


def load_data(work_root):
    # pd_data = pd.read_csv(work_root + '/data/3tier_lorenz_v3.csv', header=None).T
    # pd_data = pd.read_csv(work_root + '/data/ks_64.csv', header=None)
    pd_data = pd.read_csv(work_root + '/data/QG_everydt_avgu.csv', header=None)
    pd_data = standardize_data(pd_data)

    return np.array(pd_data)


def main():
    param_grid = {
        'group_count': [11],
        'feature_count': [88],
        'lsp': [7],
        'train_length': [100000],
        'predict_length': [1000],
        'approx_res_size': [1000],
        'radius': [0.95],
        'sigma': [0.05],
        'random_state': [42],
        'beta': list(np.logspace(np.log10(0.001), np.log10(5), num=10000)),
        'degree': [7],
    }

    shifts = list(range(0, param_grid['predict_length'][0] * 10, param_grid['predict_length'][0]))

    if rank == master_node_rank:
        work_root = os.environ['WORK']
        all_data = load_data(work_root)
    else:
        all_data = None
        work_root = None

    MAX_EVALS = 500000
    for i in range(MAX_EVALS):

        if rank == master_node_rank:
            params = {k: random.sample(v, 1)[0] for k, v in param_grid.items()}
            print_with_rank(str(params))
        else:
            params = None

        params = comm.bcast(params, master_node_rank)

        for shift in shifts:
            if rank == master_node_rank:
                data = all_data[:, shift: params['train_length'] + shift]
            else:
                data = None

            output = ESNParallel(**params).fit(data).predict()

            if rank == master_node_rank:
                params['shift'] = shift
                shift_folder = dict_to_string({k: v for k, v in params.items() if k != 'shift'})
                directory = os.path.join(work_root, 'random_shift_results', shift_folder)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                result_path = os.path.join(directory, 'data=QG-' + dict_to_string(params) + '.txt')
                np.savetxt(result_path, output)
                print_with_rank("Saved to " + result_path)
                del params['shift']


if __name__ == '__main__':
    main()
