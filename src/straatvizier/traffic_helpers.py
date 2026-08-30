from straatvizier.analysis import MODES


def requested_directions(direction_choice):
    if direction_choice == "Richtingen apart tonen":
        return ["ab", "ba"]

    if direction_choice == "A → B":
        return ["ab"]

    if direction_choice == "B → A":
        return ["ba"]

    return ["both"]

def traffic_label_for(labels):
    modes = [MODES[label] for label in labels]

    if set(modes) == {"car", "heavy"}:
        return "Gemotoriseerd verkeer"

    if len(labels) == 1:
        return labels[0]

    return " + ".join(labels)

def mode_flags(selected_modes):
    return {
        "include_car": "car" in selected_modes,
        "include_bike": "bike" in selected_modes,
        "include_heavy": "heavy" in selected_modes,
        "include_pedestrian": "pedestrian" in selected_modes,
    }

