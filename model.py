import torch
import torch.nn as nn
import torch.nn.functional as F

class PointerNet(nn.Module):
    def __init__(self, input_dim=2, hidden_dim=128):
        super(PointerNet, self).__init__()
        self.hidden_dim = hidden_dim
        
        # Encoder: Học đặc trưng không gian của các điểm
        self.encoder = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        
        # Attention Mechanism: Quyết định xem điểm nào là quan trọng nhất tiếp theo
        self.W1 = nn.Linear(hidden_dim, hidden_dim)
        self.W2 = nn.Linear(hidden_dim, hidden_dim)
        self.V = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        # x shape: (1, num_nodes, 2)
        encoder_outputs, (h, c) = self.encoder(x)
        
        # Đơn giản hóa: Dùng hidden state cuối làm Query
        query = h[-1].unsqueeze(1) # (1, 1, hidden_dim)
        
        # Tính toán Attention scores (Logits)
        # score = V * tanh(W1*ref + W2*query)
        ref = self.W1(encoder_outputs) # (1, num_nodes, hidden_dim)
        query_layer = self.W2(query)     # (1, 1, hidden_dim)
        
        scores = self.V(torch.tanh(ref + query_layer)).squeeze(-1) # (1, num_nodes)
        return scores