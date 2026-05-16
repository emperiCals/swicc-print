from typing import List, Tuple, Dict, Any

def plan_vector_drawing_commands(contours: List[List[Tuple[int, int]]], start_pos: Tuple[int, int] = (128, 128)) -> List[Dict[str, Any]]:
    commands = []
    curr_pos = start_pos
    remaining_contours = list(contours)
    
    while remaining_contours:
        best_idx = 0
        best_dist = float('inf')
        reverse_required = False
        
        # 计算全局最优空移距离，动态评估正向或反向接入端点
        for idx, contour in enumerate(remaining_contours):
            dist_to_start = abs(contour[0][0] - curr_pos[0]) + abs(contour[0][1] - curr_pos[1])
            dist_to_end = abs(contour[-1][0] - curr_pos[0]) + abs(contour[-1][1] - curr_pos[1])
            
            if dist_to_start < best_dist:
                best_dist = dist_to_start
                best_idx = idx
                reverse_required = False
            if dist_to_end < best_dist:
                best_dist = dist_to_end
                best_idx = idx
                reverse_required = True
                
        contour = remaining_contours.pop(best_idx)
        if reverse_required:
            contour.reverse()
            
        # 1. 抬笔空移至当前矢量轮廓的起始点
        start_pt = contour[0]
        dx = start_pt[0] - curr_pos[0]
        dy = start_pt[1] - curr_pos[1]
        if dx != 0 or dy != 0:
            commands.append({"type": "move", "dx": dx, "dy": dy})
            
        # 2. 触发落笔状态机转换
        commands.append({"type": "pen_down"})
        
        # 3. 连续保持画笔闭合，阶跃跟踪各轮廓节点
        for i in range(1, len(contour)):
            pt = contour[i]
            prev_pt = contour[i-1]
            commands.append({"type": "move", "dx": pt[0] - prev_pt[0], "dy": pt[1] - prev_pt[1]})
            
        # 4. 结束当前路径，恢复抬笔状态
        commands.append({"type": "pen_up"})
        curr_pos = contour[-1]
        
    return commands