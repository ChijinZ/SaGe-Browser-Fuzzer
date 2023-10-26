import shutil

import grammar
import pickle
from grammar import DerivationTreeNode, DerivationTree, InvalidNode, StatisticsForRule
from typing import List, Dict, Tuple, Optional, Set
import threading
import sys
import os
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import gc
from operator import itemgetter
from pympler import tracker
import argparse

MAX_PARENT_LIMIT = 5

# rule name -> index
global_map: Dict[str, int] = {}
# list of rule name
global_list: List[str] = []

update_info_lock = threading.Lock()

last_file_sys_time: float = time.perf_counter()
last_merged_time: float = time.perf_counter()


def merge_to_statistics_map(target_map: Dict[int, StatisticsForRule], source_map: Dict[int, StatisticsForRule]):
    for key, statistics in source_map.items():
        if key not in target_map:
            target_map[key] = StatisticsForRule(key)

        target_statistics = target_map[key]

        for parent_tuple, statistics_result in statistics.parent_chains.items():
            if parent_tuple not in target_statistics.parent_chains:
                target_statistics.parent_chains[parent_tuple] = [0, 0]

            target_statistics.parent_chains[parent_tuple][0] += statistics_result[0]
            target_statistics.parent_chains[parent_tuple][1] += statistics_result[1]


def get_global_info_from_path(path_list: List[str]) -> Set[str]:
    res = set()

    for path in path_list:
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
        except BaseException as e:
            print(f"{e}")

        _tree_list: List[DerivationTree] = data[0]
        st_to_tree_map: Dict[str, DerivationTreeNode] = data[1]
        feedback: List[Tuple[str, bool]] = data[2]
        global last_file_sys_time
        for record in feedback:
            statement: str = record[0]
            _result: bool = record[1]
            try:
                tree_node: DerivationTreeNode = st_to_tree_map[statement]
            except BaseException as e:
                continue
            p = tree_node
            while p is not None:
                if not p.is_phantom:
                    st = p.rule
                    if st not in global_map:
                        res.add(st)
                p = p.parent
    return res


def traverse(current_node: DerivationTreeNode, parents: List[int],
             statistics_map: Dict[int, StatisticsForRule], result: bool, depth: int):
    assert len(parents) <= MAX_PARENT_LIMIT
    if depth > MAX_PARENT_LIMIT:
        return
    if current_node.rule not in global_map:
        return
    index = global_map[current_node.rule]
    if index not in statistics_map:
        statistics_map[index] = StatisticsForRule(index)

    if len(parents) != 0:
        statistics = statistics_map[index]
        parents_tuple = tuple(parents)
        statistics.add_a_record(parents_tuple, result)

    new_parents = [index]
    while len(new_parents) != MAX_PARENT_LIMIT and len(parents) != 0:
        new_parents.append(parents.pop())
    new_parents.reverse()
    for node in current_node.get_children():
        if node is not None:
            traverse(current_node=node, parents=new_parents.copy(), statistics_map=statistics_map, result=result,
                     depth=depth + 1)


def process_files(paths: List[str]) -> (Dict[int, StatisticsForRule], List[str]):
    statistics_map: Dict[int, StatisticsForRule] = {}
    for path in paths:
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
        except BaseException as e:
            print(f"{e}")

        tree_list: List[DerivationTree] = data[0]
        st_to_tree_map: Dict[str, DerivationTreeNode] = data[1]
        feedback: List[Tuple[str, bool]] = data[2]

        for record in feedback:
            statement: str = record[0]
            result: bool = record[1]
            try:
                tree_node: DerivationTreeNode = st_to_tree_map[statement]
                traverse(current_node=tree_node, parents=[], statistics_map=statistics_map, result=result, depth=0)
            except KeyError as e:
                pass
            except BaseException as e:
                print(e)

    # print("finish")
    return statistics_map, paths


def collect_global_info(path):
    pickle_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith("pickle"):
                pickle_files.append(root + "/" + file)

    print(f"total: {len(pickle_files)} pickle files")

    group_file_num = 10
    file_tasks = []
    cnt = 0
    for file in pickle_files:
        index = cnt // group_file_num
        while len(file_tasks) <= index:
            file_tasks.append([])
        file_tasks[index].append(file)
        cnt += 1

    print(f"slit to {len(file_tasks)} tasks")

    # for file in tqdm(pickle_files):
    #     global last_file_sys_time
    #     result: List[str] = get_global_info_from_path(file)
    #     for st in result:
    #         le = len(global_list)
    #         global_map[st] = le
    #         global_list.append(st)
    #         if time.perf_counter() - last_file_sys_time > 60:
    #             with open("./global_info.pickle", "wb+") as f:
    #                 pickle.dump((global_map, global_list), f)
    #             last_file_sys_time = time.perf_counter()

    with tqdm(total=len(file_tasks)) as pbar:

        with ProcessPoolExecutor(max_workers=19) as ex:
            futures = [ex.submit(get_global_info_from_path, file_list) for file_list in file_tasks]
            for future in as_completed(futures):
                result: Set[str] = future.result()
                for st in result:
                    if st not in global_map:
                        with update_info_lock:
                            le = len(global_list)
                            global_map[st] = le
                            global_list.append(st)
                            if time.perf_counter() - last_file_sys_time > 60:
                                with open("./global_info.pickle", "wb+") as f:
                                    pickle.dump((global_map, global_list), f)
                                last_file_sys_time = time.perf_counter()
                pbar.update(1)

    with open("./global_info.pickle", "wb+") as f:
        pickle.dump((global_map, global_list), f)


def process_data(training_path, global_info_path):
    global global_map
    global global_list

    path = training_path

    with open(global_info_path, "rb") as f:
        a, b = pickle.load(f)
        global_map = a
        global_list = b

    # global_statistics_map = {}
    visited_file_paths = set()

    if os.path.exists("./statistics_map.pickle"):
        try:
            with open("./statistics_map.pickle", "rb") as f:
                _global_statistics_map, visited_file_paths = pickle.load(f)
                del _global_statistics_map
        except BaseException as e:
            print(e)

    pickle_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith("pickle"):
                path = root + "/" + file
                if path in visited_file_paths:
                    continue
                pickle_files.append(path)

    print(f"total: {len(pickle_files)} pickle files")

    group_file_num = 100
    file_tasks = []
    cnt = 0
    for file in pickle_files:
        index = cnt // group_file_num
        while len(file_tasks) <= index:
            file_tasks.append([])
        file_tasks[index].append(file)
        cnt += 1

    print(f"slit to {len(file_tasks)} tasks")

    global last_file_sys_time
    global last_merged_time

    task_max = 10

    tmp_map = {}

    with tqdm(total=len(file_tasks)) as pbar:
        while len(file_tasks) > 0:
            print("a new task iteration")
            tmp_executor_tasks = []
            while len(file_tasks) > 0 and len(tmp_executor_tasks) < task_max:
                tmp_executor_tasks.append(file_tasks.pop())

            with ProcessPoolExecutor(max_workers=task_max) as ex:
                futures = [ex.submit(process_files, file_list) for file_list in tmp_executor_tasks]
                # print(len(futures))

                for future in as_completed(futures):
                    r = future.result()
                    statistics_map: Dict[int, StatisticsForRule] = r[0]
                    paths: List[str] = r[1]
                    for path in paths:
                        visited_file_paths.add(path)
                    # print("start merge", flush=True)
                    merge_to_statistics_map(target_map=tmp_map, source_map=statistics_map)
                    # print("merged", flush=True)

                    if time.perf_counter() - last_file_sys_time > 180:
                        if not update_info_lock.locked():
                            update_info_lock.acquire()

                            global_statistics_map = {}
                            if os.path.exists("./statistics_map.pickle"):
                                try:
                                    with open("./statistics_map.pickle", "rb") as f:
                                        print("start reading global statistics map from FS")
                                        global_statistics_map, _visited_file_paths = pickle.load(f)
                                        print("finish reading global statistics map from FS")

                                        print("start merging to global statistics map")
                                        merge_to_statistics_map(target_map=global_statistics_map, source_map=tmp_map)
                                        print("finish merging to global statistics map")
                                except BaseException as e:
                                    print(e)

                            if os.path.exists("./statistics_map.pickle"):
                                shutil.move("./statistics_map.pickle", "./statistics_map_backup.pickle")
                            with open("./statistics_map.pickle", "wb+") as f:
                                print("start writing to FS")
                                pickle.dump((global_statistics_map, visited_file_paths), f)
                                print("finish writing to FS")

                            if global_statistics_map:
                                global_statistics_map.clear()
                            if tmp_map:
                                tmp_map.clear()
                            print(gc.get_referrers(global_statistics_map))
                            del global_statistics_map
                            del tmp_map

                            time.sleep(1)
                            print(f"delete num: {gc.collect()}")
                            time.sleep(1)

                            tmp_map = {}

                            last_file_sys_time = time.perf_counter()

                            update_info_lock.release()
                    pbar.update(1)

    with open("./statistics_map.pickle", "wb+") as f:
        pickle.dump((global_statistics_map, visited_file_paths), f)


def check_if_API_invocation(rule_statement: str) -> bool:
    if "." in rule_statement or "(" in rule_statement or "[" in rule_statement:
        return True
    else:
        return False

def build_invalid_tree(global_info_path, statistics_path):
    min_delete_num = 2

    global global_map
    global global_list

    with open(global_info_path, "rb") as f:
        a, b = pickle.load(f)
        global_map = a
        global_list = b

    global_statistics_map: Dict[int, StatisticsForRule] = {}
    _visited_file_paths: Set[str] = set()

    with open(statistics_path, "rb") as f:
        global_statistics_map, _visited_file_paths = pickle.load(f)

    invalid_node_dic: Dict[int, InvalidNode] = {}
    cnt = 0
    for rule_index, statistics in tqdm(global_statistics_map.items()):
        for parents, result in statistics.parent_chains.items():
            # print(result)
            assert result[0] != 0, result
            if not check_if_API_invocation(global_list[parents[0]]):
                continue

            if (result[0] - result[1]) / result[0] < 0.1 and result[0] > min_delete_num and len(parents) > 0:
                if len(parents) == MAX_PARENT_LIMIT:
                    print(f"we found one: {result}: {[global_list[x] for x in parents]}, {global_list[rule_index]}")
                else:
                    print(
                        f"we found one that has less len: {result}: {[global_list[x] for x in parents]}, {global_list[rule_index]}")
                # we found one
                cnt += 1
                if rule_index not in invalid_node_dic:
                    invalid_node_dic[rule_index] = InvalidNode(rule_index)
                parent_list = list(parents)
                p = invalid_node_dic[rule_index]
                while len(parent_list) != 0:
                    parent_index = parent_list.pop()
                    if parent_index in p.children:
                        p = p.children[parent_index]
                    else:
                        new_node = InvalidNode(parent_index)
                        new_node.parent = p
                        p.children[parent_index] = new_node
                        p = new_node
    print(cnt)

    # find rules that are never correct
    incorrect_rules = set()
    for rule_index, statistics in tqdm(global_statistics_map.items()):
        for parents, result in statistics.parent_chains.items():
            incorrect_rules.add(parents[0])
            if not ((result[0] - result[1]) / result[0] < 0.1 and result[0] > min_delete_num and len(parents) > 0):
                incorrect_rules.remove(parents[0])
                break

    for rule_index in incorrect_rules:
        invalid_node_dic[rule_index] = InvalidNode(rule_index)
        print(global_list[rule_index])

    with open("./invalid_tree.pickle", "wb+") as f:
        pickle.dump(invalid_node_dic, f)


# collect_global_info -> process_data -> build_invalid_tree
if __name__ == '__main__':
    # collect_global_info()
    # process_data()
    # build_invalid_tree()
    parser = argparse.ArgumentParser(description='scrypt to construct invalid context trees')
    parser.add_argument('--procedure', type=str, help='collect_global_info/process_data/build_invalid_tree',
                        required=True)
    parser.add_argument('--training-data-path', type=str, help='directory path of training data')
    parser.add_argument('--global-info-path', type=str, help='path of global_info.pickle')
    parser.add_argument('--stats-path', type=str, help='path of statistics_map.pickle')
    args = parser.parse_args()
    if args.procedure == "collect_global_info":
        if args.training_data_path is None:
            print("please set training-data-path for collect_global_info")
            exit()
        collect_global_info(args.training_data_path)

    if args.procedure == "process_data":
        if args.training_data_path is None or args.global_info_path is None:
            print("please set training-data-path and global-info-path for process_data")
            exit()
        process_data(args.training_data_path, args.global_info_path)

    if args.procedure == "build_invalid_tree":
        if args.global_info_path is None or args.stats_path is None:
            print("please set global-info-path and stats-path for build_invalid_tree")
            exit()
        build_invalid_tree(args.global_info_path, args.stats_path)
