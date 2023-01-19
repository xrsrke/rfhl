# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/08_agent.ipynb.

# %% auto 0
__all__ = ['Agent', 'AgentLoss', 'AgentObjective', 'LitAgent']

# %% ../nbs/08_agent.ipynb 3
from typing import Callable, Tuple

import torch
from torch import nn
import torch.nn.functional as F
from torch.distributions import Categorical

from transformers import AutoModel
import pytorch_lightning as pl 
from torchtyping import TensorType

# %% ../nbs/08_agent.ipynb 4
class Agent(nn.Module):
    def __init__(self, model: Callable):
        """Initialize the agent.

        Args:
            n_observations (int): The vocab size
            model (Callable): The pre-trained language model
        """
        super().__init__()
        
        n_embd = model.config.n_embd

        self.policy_network = model        
        self.value_network = nn.Sequential(
            nn.Linear(n_embd, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Tanh()
        )
    
    def get_value(
        self, hidden_state: TensorType["batch_size", "seq_len", "n_embd"]
    ) -> TensorType["batch_size", 1]:
        return self.value_network(hidden_state)[:, -1, :]
    
    def forward(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor
    ) -> Tuple[
        TensorType["batch_size", "seq_len", "vocab_size"],
        TensorType["batch_size", "seq_len", "vocab_size"],
        TensorType["batch_size", "seq_len"],
        TensorType["batch_size", 1]
    ]:
        base_output = self.policy_network(
            input_ids, attention_mask=attention_mask,
            output_hidden_states=True
        )
        
        last_hidden_state = base_output.hidden_states[-1]
        # takes the logit of the last token
        # for each sequence in the batch
        logits = base_output.logits[:, -1, :]
        probs = F.softmax(logits, dim=-1)
                
        logprobs = probs.log()
        
        action_dist = Categorical(probs=probs)
        entropy = action_dist.entropy()
        
        # predicted reward value
        value = self.get_value(last_hidden_state).squeeze(-1)
        
        return logits, logprobs, entropy, value

# %% ../nbs/08_agent.ipynb 10
class AgentLoss(nn.Module):
    def __init__(self):
        super().__init__()
    
    def forward(self, action_logits, rejected_reward):
        pass

# %% ../nbs/08_agent.ipynb 12
class AgentObjective(nn.Module):
    def __init__(
        self, model: Callable, sft_model: Callable, reward_model: Callable,
        gamma: float, beta: float
    ):
        super().__init__()
        self.model = model
        self.sft_model = sft_model
        self.reward_model = reward_model
        self.gamma = gamma
        self.beta = beta
        
    def forward(self, input_ids: TensorType["batch", "seq_len", "n_dim"], attention_mask):
        
        model_logits = self.model(input_ids, attention_mask)
        # TODO: implement these
        model_input_ids = None
        model_attention_mask = None
        model_dist = F.softmax(model_logits, dim=-1)
        
        sft_logits = self.sft_model(input_ids, attention_mask)
        sft_dist = F.softmax(sft_logits, dim=-1)
        
        reward_score = self.reward_model(model_input_ids, model_attention_mask)
        
        ratio = torch.log(model_dist / sft_dist)
        
        # compute the coherent of the generated text
        coherent = torch.log(model_dist)
        
        objective = (reward_score - self.beta*ratio).mean() + self.gamma * coherent.mean()
        
        return objective
        

# %% ../nbs/08_agent.ipynb 13
class LitAgent(pl.LightningModule):
    def __init__(self, model: Callable, loss_func: Callable):
        super().__init__()
        self.model = model
        self.loss_func = loss_func
    
    def training_step(self, batch, batch_idx):
        pass
