import torch
import torch.optim as optim
from model import PointerNet

def train():
    # Khởi tạo mô hình
    model = PointerNet()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    print("--- Bắt đầu huấn luyện AI (Deep RL) ---")
    for epoch in range(100):
        # Tạo dữ liệu giả lập (Batch size 1, 10 điểm, tọa độ x-y)
        inputs = torch.rand(1, 10, 2)
        
        # Forward pass
        logits = model(inputs)
        
        # Loss giả định để cập nhật trọng số
        loss = torch.mean(logits**2) 
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        if epoch % 20 == 0:
            print(f"Epoch {epoch}: Đang tối ưu hóa các node...")

    # Lưu trọng số vào file .pth
    torch.save(model.state_dict(), "weights.pth")
    print("--- Đã lưu bộ não AI vào file 'weights.pth' ---")

if __name__ == "__main__":
    train()