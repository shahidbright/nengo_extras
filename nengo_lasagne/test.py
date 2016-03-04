import nengo
from nengo.params import Parameter
from nengo.processes import PresentInput
import numpy as np

import nengo_lasagne as nlg


def test_xor():
    inputs = np.asarray([[[0, 0]], [[0, 1]], [[1, 0]], [[1, 1]]],
                        dtype=np.float32)
    targets = np.asarray([[[0]], [[1]], [[1]], [[0]]], dtype=np.float32)

    with nengo.Network() as net, nlg.default_config():
        N = 10
        d = 2
        inp = nengo.Node(output=PresentInput(inputs, 0.001),
                         label="input")
        ens = nengo.Ensemble(N, d, label="ens")
        output = nengo.Node(size_in=1, label="output")

        #         nengo.Connection(inp, ens.neurons, transform=np.zeros((N, 2)))
        #         nengo.Connection(ens.neurons, output, transform=np.zeros((1, N)))
        nengo.Connection(inp, ens, transform=nlg.init.GlorotUniform())
        nengo.Connection(ens, output, transform=nlg.init.GlorotUniform())

        p = nengo.Probe(output)

    sim = nlg.Simulator(net)
    sim.model.train({inp: inputs}, {output: targets}, minibatch_size=4,
                    n_epochs=1000, l_rate=0.1)
    sim.run_steps(4)

    print(sim.data[p])


def test_fancy():
    inputs = np.asarray([np.random.uniform(-1, 1,
                                           size=(1000, 1)).astype(np.float32)
                         for _ in range(3)])
    outputs = (inputs[0] + 1) * inputs[1] ** 2 + np.sin(inputs[2])
    inputs = inputs[:, :, None]
    outputs = outputs[:, None]

    with nengo.Network() as net, nlg.default_config():
        input_nodes = [nengo.Node(output=PresentInput(x.squeeze(axis=1),
                                                      0.001),
                                  label="node_%d" % i)
                       for i, x in enumerate(inputs)]

        ens0 = nengo.Ensemble(100, 2, label="ens0")
        ens1 = nengo.Ensemble(50, 1, label="ens1")
        nengo.Connection(input_nodes[0], ens0[0])
        nengo.Connection(input_nodes[1], ens0[1])
        nengo.Connection(input_nodes[2], ens1)

        output_node = nengo.Node(size_in=1)
        nengo.Connection(ens0, output_node,
                         function=lambda x: (x[0] + 1) * x[1] ** 2)
        nengo.Connection(ens1, output_node, function=np.sin)

        p = nengo.Probe(output_node)

    sim = nlg.Simulator(net)
    sim.model.train(dict(zip(input_nodes, inputs)), {output_node: outputs},
                    n_epochs=1000, minibatch_size=100,
                    optimizer_kwargs={"learning_rate": 1e-2})
    # sim = nengo.Simulator(net)
    sim.run_steps(1000)

    print(np.sqrt(np.mean(outputs - sim.data[p]) ** 2))
    print(inputs[0][:3])
    print(inputs[1][:3])
    print(inputs[2][:3])
    print(outputs[:3])
    print(sim.data[p][:, :3])


def test_recurrent():
    batch_size = 1000
    sig_len = 10
    dt = 1e-3
    inputs = np.random.randn(batch_size, sig_len, 1).astype(np.float32)
    targets = np.cumsum(inputs, axis=1) * dt

    with nengo.Network() as net, nlg.default_config():
        input_node = nengo.Node(output=nengo.processes.WhiteNoise(scale=False))
        ens = nengo.Ensemble(50, 1)
        output_node = nengo.Node(size_in=1)

        nengo.Connection(input_node, ens)
        nengo.Connection(ens.neurons, ens.neurons,
                         transform=nlg.init.GlorotUniform())
        nengo.Connection(ens, output_node)

        input_p = nengo.Probe(input_node)
        output_p = nengo.Probe(output_node)

    sim = nlg.Simulator(net, dt=dt)
    sim.model.train({input_node: inputs}, {output_node: targets},
                    n_epochs=1000, minibatch_size=100,
                    optimizer_kwargs={"learning_rate": 1e-2})

    sim.run_steps(sig_len,
                  {input_node: np.random.randn(batch_size,
                                               sig_len, 1).astype(np.float32)})

    truth = np.cumsum(sim.data[input_p], axis=1) * dt

    print(sim.data[output_p].shape)
    print(np.sqrt(np.mean((truth - sim.data[output_p]) ** 2)))


# test_xor()
test_fancy()
# test_recurrent()