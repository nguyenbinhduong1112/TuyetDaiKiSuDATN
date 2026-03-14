import torch

def solve_delivery_route(model, coords):
    """
    model: PointerNet đã train
    coords: Tensor (num_nodes, 2)
    """
    model.eval()
    num_nodes = coords.size(0)
    visited = [0] # Bắt đầu từ kho (điểm đầu tiên)
    current_node = 0
    
    with torch.no_grad():
        for _ in range(num_nodes - 1):
            # Lấy xác suất từ model
            logits = model(coords.unsqueeze(0))
            
            # MASKING: Không chọn lại các điểm đã đi
            mask = torch.zeros(num_nodes)
            mask[visited] = -float('inf')
            masked_logits = logits + mask
            
            # Chọn điểm có điểm số cao nhất
            next_node = torch.argmax(masked_logits).item()
            visited.append(next_node)
            current_node = next_node
            
    visited.append(0) # Quay về kho
    return visited