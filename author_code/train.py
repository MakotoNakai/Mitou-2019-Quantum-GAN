#!/usr/bin/env python

"""
    training_pure_state.py: training process of qwgan for pure state

"""
from datetime import datetime
from PIL import Image
from qiskit import *
import matplotlib.pyplot as plt
import time

from model.model_pure import Generator, Discriminator, compute_fidelity, compute_cost, get_zero_state
from tools.plot_hub import plt_fidelity_vs_iter
from tools.utils import save_model, train_log
from tools.qcircuit import *
import config_pure as cf

from frqi.frqi import *
from generator.circuit import *


np.random.seed()
size = cf.system_size


def main():

    # 生成したい画像
    testimg = [[255,255,255,255], [0, 0, 0, 0], [255, 255, 255, 255], [0, 0, 0, 0]]
    
    nqubits = 6
    control = [num for num in range(1,5)]
    target = 0
    anc = [nqubits-1]

    # 各ステップのフィデリティー
    fidelities = list()
    
    #各ステップのコスト関数
    losses = list()

    # 学習する量子状態 関数get_real_state4は ./frqi/frqi.pyをご覧下さい
    real_state = get_real_state4(QuantumCircuit(nqubits), testimg, control, target, anc).T
    
    # Generator
    zero_state = get_zero_state(size)
    gen = Generator(size)
    
    # Generatorの量子回路を設置する　関数circ_frqiEncoderに関しては ./generator/circuit.py及び
    #./generator/gates.pyをご覧下さい 
    gen.set_qcircuit(circ_frqiEncoder(gen.qc, testimg, control, target, anc))

    # Discriminator
    herm = [I, Pauli_X, Pauli_Y, Pauli_Z]

    dis = Discriminator(herm, size)

    f = compute_fidelity(gen,zero_state,real_state)
    # optional term, this is for controlling the initial fidelity is small.
    # while(compute_fidelity(gen,zero_state,real_state)>0.5):
    #     gen.reset_angles()
    while(compute_fidelity(gen,zero_state,real_state)<0.001):
        gen.reset_angles()

    # 学習
    while(f < 0.99):
        starttime = datetime.now()
        for iter in range(cf.epochs):
            print("==================================================")
            print("Epoch {}, Step_size {}".format(iter + 1, cf.eta))

            if iter % cf.step_size == 0:
                # Generator gradient descent
                gen.update_gen(dis,real_state)
                print("Loss after generator step: {}".format(compute_cost(gen, dis,real_state)))

            # Discriminator gradient ascent
            dis.update_dis(gen,real_state)
            print("Loss after discriminator step: {}".format(compute_cost(gen, dis,real_state)))

            cost = compute_cost(gen, dis, real_state)
            fidelity = compute_fidelity(gen, zero_state, real_state)

            losses.append(cost)
            fidelities.append(fidelity)

            print("Fidelity between real and fake state: {}".format(fidelity))
            print("==================================================")

            if iter % 10 == 0:
                endtime = datetime.now()
                training_duration = (endtime - starttime).seconds / np.float(3600)
                param = 'epoches:{:4d} | fidelity:{:8f} | time:{:10s} | duration:{:8f}\n'.format(iter,round(fidelity,6),time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),round(training_duration,2))
                train_log(param, './{}qubit_log_pure.txt'.format(cf.system_size))

            if (cf.decay):
                eta = (cf.initial_eta * (cf.epochs - iter - 1) +
                       (cf.initial_eta) * iter) / cf.epochs

        f = compute_fidelity(gen,zero_state,real_state)

    plt_fidelity_vs_iter(fidelities, losses, cf, indx=0)
    save_model(gen, cf.model_gen_path)
    save_model(dis, cf.model_dis_path)
    
    fidelities[:]=[]
    losses[:]=[]

    
    real_matrix = frqiDecoder2(real_state)
    fake_matrix = frqiDecoder2(gen.getState())
    
    real_image = Image.fromarray(real_matrix)
    real_image.save('real_image.png')
#     plt.imsave('real_img.jpg', real_matrix, cmap='gray')


if __name__ == '__main__':

    main()


