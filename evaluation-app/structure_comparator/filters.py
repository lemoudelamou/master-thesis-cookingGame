def filter_tasks(gt_tasks, gen_tasks, search_term):
    filtered_gt = gt_tasks
    filtered_gen = gen_tasks
    if search_term:
        filtered_gt = [t for t in gt_tasks if search_term.lower() in str(t.get("name", "")).lower()]
        filtered_gen = [t for t in gen_tasks if search_term.lower() in str(t.get("name", "")).lower()]
    return filtered_gt, filtered_gen


def filter_transitions(gt_transitions, gen_transitions, search_term):
    filtered_gt = gt_transitions
    filtered_gen = gen_transitions
    if search_term:
        filtered_gt = [t for t in gt_transitions if search_term.lower() in str(t.get("parent", "")).lower()]
        filtered_gen = [t for t in gen_transitions if search_term.lower() in str(t.get("parent", "")).lower()]
    return filtered_gt, filtered_gen
