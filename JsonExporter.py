import http.client
import json
import os
import re

NUM_SUFFIX = "[num]"
RECORD_LIMIT = 1000
class SendError(Exception):
    pass

def main(host, token, table_id, view_id, output_file):
    # 配置
    headers = {'xc-token': token}
    
    # 临时调试文件路径
    tmp_dir = "./debug"
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    step1_file = os.path.join(tmp_dir, "debug_step1_columns.json")
    step2_file = os.path.join(tmp_dir, "debug_step2_column_details.json")
    step2_file_2 = os.path.join(tmp_dir, "debug_step2_column_maps.json")
    step3_file = os.path.join(tmp_dir, "debug_step3_data.json")

    #####################################################################
    # 1. 获取所有 column meta 信息
    try:
        conn = http.client.HTTPConnection(host)
        columns_path = f"/api/v2/meta/views/{view_id}/columns"
        conn.request("GET", columns_path, headers=headers)
        res = conn.getresponse()
        if res.status != 200:
            raise SendError(f"通信失败 \n{res.status} {res.reason}")
        columns_data = res.read()
        conn.close()
        # 保存第一步返回
        with open(step1_file, "wb") as f:
            f.write(columns_data)
    except Exception as e:
        raise SendError(f"第一步：获取 Column Meta 信息异常: {e}")
    
    try:
        columns_info = json.loads(columns_data.decode("utf-8"))
        column_ids = [item["fk_column_id"] for item in columns_info.get("list", [])]
    except Exception as e:
        raise SendError(f"第一步：解析 Column Meta 信息失败: {e}")
    
    #####################################################################
    # 2. 获取每个 column 的 title、uidt、dt
    column_detail_tpl = "/api/v2/meta/columns/{column_id}"
    column_map = {}
    column_details = []
    all_col_json = {}
    # 收集所有列详情
    for col_id in column_ids:
        try:
            path = column_detail_tpl.format(column_id=col_id)
            conn = http.client.HTTPConnection(host)
            conn.request("GET", path, headers=headers)
            res = conn.getresponse()
            if res.status != 200:
                raise SendError(f"通信失败 {res.status} {res.reason} (column_id={col_id})")
            col_data = res.read()
            conn.close()

            col_json = json.loads(col_data.decode("utf-8"))
            column_details.append(col_json)
            all_col_json[col_json.get("id")] = col_json
        except Exception as e:
            raise SendError(f"第二步： column {col_id} 返回数据失败: {e}")

    # 构建 column_map，并处理 Lookup 关联类型
    try:
        for col_json in column_details:
            title = col_json.get("title")
            uidt = col_json.get("uidt")
            dt = col_json.get("dt")
            lookup_relation_type = None
            if uidt == "Lookup":
                fk_relation_column_id = None
                col_options = col_json.get("colOptions")
                if col_options:
                    fk_relation_column_id = col_options.get("fk_relation_column_id")
                if fk_relation_column_id and fk_relation_column_id in all_col_json:
                    related_col = all_col_json[fk_relation_column_id]
                    related_col_options = related_col.get("colOptions")
                    if related_col_options:
                        lookup_relation_type = related_col_options.get("type")
            if title:
                column_map[title] = {"uidt": uidt, "dt": dt, "lookup_relation_type": lookup_relation_type}
    except Exception as e:
            raise SendError(f"第二步：解析 column 返回数据失败: {e}")
    
    # 保存第二步所有详情
    with open(step2_file, "w", encoding="utf-8") as f:
        json.dump(column_details, f, ensure_ascii=False, indent=2)
    with open(step2_file_2, "w", encoding="utf-8") as f:
        json.dump(column_map, f, ensure_ascii=False, indent=2)
    
    #####################################################################
    # 3. 获取所有数据  
    try:
        data_api = f"/api/v2/tables/{table_id}/records?viewId={view_id}&limit={RECORD_LIMIT}"
        conn = http.client.HTTPConnection(host)
        conn.request("GET", data_api, headers=headers)
        res = conn.getresponse()
        if res.status != 200:
            raise SendError(f"通信失败 \n{res.status} {res.reason}")
        data = res.read()
        conn.close()
        # 保存第三步返回
        with open(step3_file, "wb") as f:
            f.write(data)

        data_json = json.loads(data.decode("utf-8"))
        data_list = data_json.get("list", [])
    except Exception as e:
            raise SendError(f"第三步：获取表格数据异常: {e}")
    
    #####################################################################
    # 4. 根据 column title 查找 uidt 和 dt，自定义处理（示例：类型转换）
    def process_value(value, uidt, dt, title=None,lookup_relation_type=None):
        # 跳过 Links 字段
        if uidt in ("Links","LinkToAnotherRecord"):
            return None
        # 先处理 Lookup 类型
        if uidt == "Lookup":
            if lookup_relation_type in ("mm", "hm"):
                # 关联类型为多对多或多对一，数据为数组，对每个元素递归处理
                if isinstance(value, (list, tuple)):
                    return [process_value(v, None, None,title) for v in value]
                else:
                    return None
        # 处理 JSON 类型
        if uidt == "JSON":
            if isinstance(value, str) and value:
                try:
                    return json.loads(value)
                except Exception:
                    return value  # 解析失败则返回原字符串
            return value
        
        if value is None:
            return None
        if title and title.endswith(NUM_SUFFIX):
            try:
                match = re.match(r"^\s*(-?\d+(\.\d+)?)", value)
                if match:
                    num_str = match.group(1)
                    return float(num_str) if "." in num_str else int(num_str)
                else:
                    return value
            except Exception:
                return value
        if dt == "integer":
            try:
                return int(value)
            except Exception:
                return value
        if dt == "decimal":
            try:
                return float(value)
            except Exception:
                return value
        if dt == "boolean":
            return bool(value)
        if dt == "varchar":
            if isinstance(value, str):
                return value.strip()
        if dt == "text":
            return str(value) if value is not None else ""
        return value

    def set_nested_value(d, keys, value):
        """辅助函数：根据 keys 列表递归设置嵌套字典的值"""
        for key in keys[:-1]:
            if key not in d or not isinstance(d[key], dict):
                d[key] = {}
            d = d[key]
        d[keys[-1]] = value

    # 开始处理数据的转换
    processed_data = []
    for row in data_list:
        new_row = {}
        for k, v in row.items():
            if k == "Id":
                continue  # 跳过 Id 字段
            if v  in (None ,[]):
                continue  # 跳过空的字段
            col_info = column_map.get(k)
            lookup_relation_type = col_info.get("lookup_relation_type") if col_info else None
            processed_v = process_value(v, col_info["uidt"], col_info["dt"], k,lookup_relation_type) if col_info else v
            if processed_v in (None ,[]):
                continue # 跳过空的字段
            
            # 去掉 [num] 后缀
            if k.endswith(NUM_SUFFIX):
                key_name = k.replace(NUM_SUFFIX, "").rstrip()
            else:
                key_name = k
            if "." in key_name:
                keys = key_name.split(".")
                set_nested_value(new_row, keys, processed_v)
            else:
                new_row[key_name] = processed_v

        processed_data.append(new_row)
    
    #####################################################################
    # 5. 保存处理后的数据
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise SendError(f"保存文件失败: {e}")