import osmnx as ox
import networkx as nx
import streamlit as st

class MapManager:
    def __init__(self, place_name="Vinh, Nghe An, Vietnam"):
        if 'graph' not in st.session_state:
            with st.spinner("Đang nạp bản đồ giao thông Vinh..."):
                # Lấy dữ liệu giao thông thực tế quanh ĐH Vinh
                G = ox.graph_from_point((18.6601, 105.6942), dist=3000, network_type='drive')
                st.session_state.graph = ox.project_graph(G)
        self.G = st.session_state.graph

    def get_nearest_nodes(self, coords):
        lats, lons = coords[:, 0], coords[:, 1]
        return ox.distance.nearest_nodes(self.G, X=lons, Y=lats)

    def get_route_coords(self, node_indices):
        full_path = []
        # Thêm node đầu tiên vào cuối để tạo vòng lặp quay về Kho
        nodes_to_visit = list(node_indices) + [node_indices[0]]
        
        for i in range(len(nodes_to_visit) - 1):
            try:
                # Tìm đường ngắn nhất giữa 2 điểm dựa trên đồ thị giao thông
                path = nx.shortest_path(self.G, nodes_to_visit[i], nodes_to_visit[i+1], weight='length')
                # Lấy tọa độ kinh độ/vĩ độ của từng đoạn đường nhỏ
                path_coords = [(self.G.nodes[n]['y'], self.G.nodes[n]['x']) for n in path]
                full_path.extend(path_coords)
            except nx.NetworkXNoPath:
                continue 
        return full_path