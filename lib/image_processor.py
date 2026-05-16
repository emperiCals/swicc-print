from PIL import Image
from typing import List, Tuple

def extract_vector_contours(image_path: str, canvas_width: int = 256, canvas_height: int = 256) -> List[List[Tuple[int, int]]]:
    img = Image.open(image_path)
    img = img.resize((canvas_width, canvas_height), Image.Resampling.NEAREST)
    img = img.convert("RGBA")
    
    # 构建二值化可绘制图像特征矩阵
    mask = []
    for y in range(canvas_height):
        row = []
        for x in range(canvas_width):
            r, g, b, a = img.getpixel((x, y))
            # 过滤高亮底色与全透明通道，保留有效前景轮廓
            if a > 0 and not (r > 240 and g > 240 and b > 240):
                row.append(True)
            else:
                row.append(False)
        mask.append(row)
        
    visited = [[False for _ in range(canvas_width)] for _ in range(canvas_height)]
    contours = []
    
    # 采用 8 邻域搜索算子维持轮廓连通性
    neighbor_offsets = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
    
    for y in range(canvas_height):
        for x in range(canvas_width):
            if mask[y][x] and not visited[y][x]:
                path = []
                stack = [(x, y)]
                visited[y][x] = True
                
                while stack:
                    curr_x, curr_y = stack.pop()
                    path.append((curr_x, curr_y))
                    
                    # 贪婪跟踪最邻近未访问点以确保轨迹连续性
                    for dx, dy in neighbor_offsets:
                        nx, ny = curr_x + dx, curr_y + dy
                        if 0 <= nx < canvas_width and 0 <= ny < canvas_height:
                            if mask[ny][nx] and not visited[ny][nx]:
                                visited[ny][nx] = True
                                stack.append((nx, ny))
                                break
                                
                if len(path) > 1:
                    contours.append(path)
                    
    return contours