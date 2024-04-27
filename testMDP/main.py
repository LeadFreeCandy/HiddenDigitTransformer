from .MDP import *
from PPO.base_model import *
import copy
from PPO.PPO import clippedLossVector
import numpy as np
import torch
import matplotlib.pyplot as plt

device = torch.device('cuda')

def generate_sequence(model, mdp, batches):
    """Generate sequence of states generated by the model's policy"""
    x = torch.tensor(mdp.get_start_state(batches)).to(device)
    generated_actions =  None
    tgt = None
    rewards = torch.zeros(batches)
    for i in range(5):
        policy = model(x, tgt)
        actions = torch.argmax(policy, dim=-1).detach().cpu()[:, -1]
        if generated_actions is None:
            generated_actions = actions.unsqueeze(1)
        else:
            generated_actions = torch.concat((generated_actions, actions.unsqueeze(1)), dim=1)
        actions = actions.numpy()
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

    return x, tgt, generated_actions.to(device), rewards.to(device)

def trainPPO(model, device, mdp, epochs, sub_epochs, batch_size, eps, c_1, optim):
    model_old = copy.deepcopy(model)
    loss = clippedLossVector()
    losses = []
    rewards = []
    for e in range(epochs):
        src, gen, acts, reward = generate_sequence(model, mdp, batch_size)

        # Generate EOS mask
        states = torch.argmax(gen, dim=-1)
        eos = (states == 1) | (states == 2) | (states == 4)
        first_eos = (eos.cumsum(dim=1) == 1)
        eos_mask = torch.logical_xor(eos, first_eos)
        eos_mask = torch.logical_not(eos_mask)

        temp_model = copy.deepcopy(model)
        avg_loss = 0
        for s_e in range(sub_epochs):
            optim.zero_grad()
            l = loss(model, model_old, eps, c_1, src, gen, acts, reward, eos_mask, device)
            l.backward()
            optim.step()
            avg_loss+=l.item()

        avg_loss = avg_loss/sub_epochs
        losses.append(avg_loss)
        avg_reward = reward.sum()/batch_size
        rewards.append(avg_reward.item())
        print("EPOCH", e+1)
        print("Average Loss", avg_loss)
        print("Average Reward", avg_reward)
        print("="*10)

        model_old = temp_model
    torch.save(model.state_dict(), "temp_model.pth")
    return losses, rewards



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
    batch_size = 256
    mdp = basicMDP()
    model = BaseVectors(device=device, max_len=6, num_tokens=2, src_dim=6, tgt_dim=6, dim=6, \
            nhead=2, num_encoders=1, num_decoders=1, d_feedforward=32).to(device)
    x = torch.tensor(mdp.get_start_state(batch_size)).to(device)

    x, seq, a, r = generate_sequence(model, mdp, 2)

    optim = torch.optim.Adam(model.parameters())
    losses, rewards = trainPPO(model, device, mdp, 100, 64, batch_size, 0.2, 1, optim)
    T = [i for i in range(len(losses))]
    fig, ax = plt.subplots(2)
    ax[0].plot(T, losses)
    ax[1].plot(T, rewards)
    plt.show()

if __name__ == "__main__":
    testMDP()
