from .MDP import *
from PPO.base_model import *
import numpy as np
import torch

device = torch.device('cuda')

def generate_sequence(model, mdp, batches):
    """Generate sequence of states generated by the model's policy"""
    x = torch.tensor(mdp.get_start_state(batches)).to(device)
    tgt = None
    rewards = torch.zeros(batches)
    for i in range(5):
        policy = model(x, tgt)
        actions = torch.argmax(policy, dim=-1).detach().cpu().numpy()[:, -1]
        state_numpy = x.detach().cpu().numpy()

        if tgt is not None:
            tgt_numpy = tgt.detach().cpu().numpy()
            state_numpy = tgt_numpy[:, -1, :]
        else:
            state_numpy = state_numpy.reshape((state_numpy.shape[0], state_numpy.shape[2]))

        x_next, r, _ = mdp.batched_step(state_numpy, actions)

        rewards = rewards + r

        x_next_torch = torch.tensor(x_next).to(device).unsqueeze(1)

        if tgt is None:
            tgt = x_next_torch
        else:
            tgt = torch.concat((tgt, x_next_torch), dim=1)

    return torch.concat((x,tgt), dim=1), rewards



def main():
    mdp = basicMDP()
    start = mdp.get_start_state(5).astype(np.int32)
    actions = np.zeros(5).astype(np.int32)
    next_, r, t = mdp.batched_step(start, actions)
    print(next_)
    print(r)
    print(t)



def testMDP():
    """Use transformer for the sake of debugging"""
    batch_size = 32
    mdp = basicMDP()
    model = BaseVectors(device=device, max_len=6, num_tokens=2, src_dim=6, tgt_dim=6, dim=6, \
            nhead=2, num_encoders=1, num_decoders=1, d_feedforward=32).to(device)
    x = torch.tensor(mdp.get_start_state(batch_size)).to(device)
    print(model(x, None).shape)

    seq, r = generate_sequence(model, mdp, 2)
    print(seq)
    print(r)

if __name__ == "__main__":
    testMDP()