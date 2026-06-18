import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "脚本" / "3.0"
sys.path.insert(0, str(SCRIPT_DIR))

from r3a_v2_selector import _extract_entity, select_counterevidence_v2


def test_spices_vs_science_fiction_rejects_anchor_mismatch():
    question = "Did Susan decide to avoid spices completely due to her past discomfort with them on June 25, 2028?"
    raw_memories = [
        "User has recently started reading science fiction novels, a shift from previously avoiding them because of complex plots and futuristic settings."
    ]
    result = select_counterevidence_v2(question, raw_memories)
    assert not result["triggered"]
    assert any(r["reject_reason"] == "premise_anchor_mismatch" for r in result["rejected"])


def test_wellness_coach_retirement_vs_goals_rejects_wrong_slot():
    question = "Did Susan Thompson retire from her role as a wellness coach before August 15, 2029?"
    raw_memories = [
        "User's life goals are to achieve optimal health and wellness, manage post-menopausal symptoms without medication, and attend wellness workshops."
    ]
    result = select_counterevidence_v2(question, raw_memories)
    assert not result["triggered"]
    assert any(r["reject_reason"] in {"slot_mismatch", "not_refuting"} for r in result["rejected"])


def test_dated_shift_likes_documentaries_only_rejects():
    question = "Did Martin's movie preference shift from fictional narratives to documentaries after a relaxing week on Jan 19, 2027?"
    raw_memories = [
        "User likes documentaries because they are informative and provide real-world insights."
    ]
    result = select_counterevidence_v2(question, raw_memories)
    assert not result["triggered"]
    assert any(r["reject_reason"] in {"temporal_mismatch", "not_refuting", "absence_not_refutation"} for r in result["rejected"])


def test_after_film_festival_old_dislike_rejects():
    question = "Did Steven Miller maintain his dislike for romantic comedies after the film festival on 2027-08-22?"
    raw_memories = [
        "User dislikes romantic comedies because they are predictable and not engaging."
    ]
    result = select_counterevidence_v2(question, raw_memories)
    assert not result["triggered"]
    assert any(r["reject_reason"] in {"temporal_mismatch", "not_refuting"} for r in result["rejected"])


def test_clear_stopped_case_passes():
    question = "Does Martin still play boxing?"
    raw_memories = [
        "Martin stopped playing boxing last month and now prefers swimming."
    ]
    result = select_counterevidence_v2(question, raw_memories)
    assert result["triggered"]
    assert result["evidence"][0]["relation"] == "REFUTES_PREMISE"
    assert result["evidence"][0]["gate_trace"]["explicit_refutation"]["passed"] is True


def test_clear_switched_case_passes():
    question = "Does Michelle still drink flavored sparkling water?"
    raw_memories = [
        "Michelle switched from flavored sparkling water to plain water in November 2030."
    ]
    result = select_counterevidence_v2(question, raw_memories)
    assert result["triggered"]


def test_absence_is_not_refutation_rejects():
    question = "Did Donna ever mention having siblings?"
    raw_memories = [
        "Donna's parents are alive, married, and live nearby."
    ]
    result = select_counterevidence_v2(question, raw_memories)
    assert not result["triggered"]
    assert any(r["reject_reason"] in {"absence_not_refutation", "not_refuting", "slot_mismatch"} for r in result["rejected"])


def test_express_dislike_romantic_comedies_positive_memory_passes():
    q = "Did Sharon Brown express a dislike for romantic comedies during her discussion on February 26, 2035?"
    mem = ["User likes romantic comedies because they are lighthearted and emotionally warm."]
    assert select_counterevidence_v2(q, mem)["triggered"]


def test_find_crowded_tourist_spots_conducive_dislike_passes():
    q = "Did Taylor David find crowded tourist spots conducive to planning during his trip on Oct 31, 2028?"
    mem = ["User prefers quiet, purposeful travel experiences and dislikes crowded tourist spots, luxury travel, and high-speed tours."]
    assert select_counterevidence_v2(q, mem)["triggered"]


def test_favorite_canned_soup_avoidance_passes():
    q = "Did Sarah Garcia express frustration about canned soups being her favorite meal on Oct 18, 2031?"
    mem = ["User avoids canned soup because it tastes processed and lacks freshness."]
    assert select_counterevidence_v2(q, mem)["triggered"]


def test_health_remain_affected_later_improving_passes():
    q = "Did Sharon Brown's physical health status remain 'Affected' after September 20, 2027?"
    mem = ["User's physical health status changed from 'Normal' to 'Affected' and was later noted as 'Improving'."]
    assert select_counterevidence_v2(q, mem)["triggered"]


def test_health_change_to_bad_but_optimistic_energetic_passes():
    q = "Did Taylor David's mental health status change to 'Fatigued and Overwhelmed' on September 28, 2029?"
    mem = ["Assistant observed that User's mental health status transitioned from 'Positive and Sunny' to 'Optimistic and Energetic'."]
    assert select_counterevidence_v2(q, mem)["triggered"]


def test_health_remain_moderate_stressed_but_excellent_passes():
    q = "Did Steven Miller's health status remain moderate and stressed after retiring on Jun 15, 2029?"
    mem = ["Assistant noted that User's physical health status has progressed from 'Good and Active' to 'Excellent and Energetic'."]
    assert select_counterevidence_v2(q, mem)["triggered"]


def test_classic_games_vs_classic_elegance_rejects():
    q = "Did Joseph Garcia dislike the remastered classic adventure games he played on August 24, 2033?"
    mem = ["User enjoys synchronized swimming for its graceful, Esther-Williams-like elegance, plays tennis for strategic elegance, and practices ballroom dancing."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_salads_vs_energy_drinks_rejects():
    q = "Did Donald Smith prefer light salads over hearty grain salads during his campaign days on Dec 27, 2032?"
    mem = ["User avoids energy drinks, soda, and alcoholic drinks, preferring green tea for its calming effect during campaign situations."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_techno_after_event_old_dislike_rejects_temporal():
    q = "Did Susan Thompson decide to avoid techno music after visiting her friend's house on 2030-01-15?"
    mem = ["User dislikes heavy metal, techno, pop, and rap due to loud, fast-paced sounds that raise stress."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_dynamic_storytelling_vs_historical_fiction_rejects():
    q = "Did Sarah Garcia express a dislike for dynamic storytelling in puzzle games on April 5, 2032?"
    mem = ["Assistant recommended using love for historical fiction and biographies to inspire storytelling or creative workshops."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_pop_music_meaningful_lyrics_vs_general_music_rejects():
    q = "Did Christopher dislike pop music with meaningful lyrics during the workshop on May 10, 2031?"
    mem = ["User dislikes loud, repetitive pop songs and usually prefers classical music."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_avocado_toast_additions_vs_plain_avocado_toast_rejects():
    q = "Did Donna like the idea of adding poached eggs and cherry tomatoes to his avocado toast?"
    mem = ["User enjoys avocado toast as a quick breakfast."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_avoiding_technology_in_travel_vs_cultural_immersion_rejects():
    q = "Did Joseph express a preference for avoiding technology in his travel experiences?"
    mem = ["User prefers group tours focused on cultural immersion and local history."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_hyderabadi_biryani_vs_generic_biryani_rejects():
    q = "Did Taylor David express a dislike for Hyderabadi biryani during dinner?"
    mem = ["User likes biryani and often orders it for family meals."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_science_fiction_ethical_dilemmas_vs_generic_scifi_rejects():
    q = "Did Susan dislike science fiction novels with ethical dilemmas?"
    mem = ["User enjoys science fiction novels for futuristic settings and worldbuilding."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_action_movies_unrealistic_science_vs_science_games_rejects():
    q = "Did Martin dislike action movies with unrealistic science?"
    mem = ["User enjoys science-themed strategy games and puzzle games."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_beach_vacations_over_cultural_trips_vs_adventure_sports_rejects():
    q = "Did Sharon Brown prefer beach vacations over culturally engaging trips?"
    mem = ["User enjoys adventure-sports trips that involve hiking and kayaking."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_solo_strategy_over_multiplayer_vs_generic_strategy_games_rejects():
    q = "Did Donald Smith prefer solo strategy games over multiplayer ones?"
    mem = ["User enjoys strategy games and technology simulations."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_healthcare_industry_not_user_health_status_rejects():
    q = "Did Taylor David's mental health status change to 'Fatigued and Overwhelmed' on September 28, 2029?"
    mem = ["Taylor David's father works in the healthcare industry, which inspired an interest in health careers."]
    assert not select_counterevidence_v2(q, mem)["triggered"]


def test_christopher_dislike_entity_extraction_does_not_swallow_predicate():
    assert _extract_entity("Did Christopher dislike pop music with meaningful lyrics?") == "Christopher"
    assert _extract_entity("Did Christopher Anderson express a dislike for romantic comedies?") == "Christopher Anderson"
    assert _extract_entity("Did Donald Smith prefer light salads over hearty grain salads?") == "Donald Smith"
    assert _extract_entity("Did Williams Daniel dislike science fiction?") == "Williams Daniel"


if __name__ == "__main__":
    test_spices_vs_science_fiction_rejects_anchor_mismatch()
    test_wellness_coach_retirement_vs_goals_rejects_wrong_slot()
    test_dated_shift_likes_documentaries_only_rejects()
    test_after_film_festival_old_dislike_rejects()
    test_clear_stopped_case_passes()
    test_clear_switched_case_passes()
    test_absence_is_not_refutation_rejects()
    test_express_dislike_romantic_comedies_positive_memory_passes()
    test_find_crowded_tourist_spots_conducive_dislike_passes()
    test_favorite_canned_soup_avoidance_passes()
    test_health_remain_affected_later_improving_passes()
    test_health_change_to_bad_but_optimistic_energetic_passes()
    test_health_remain_moderate_stressed_but_excellent_passes()
    test_classic_games_vs_classic_elegance_rejects()
    test_salads_vs_energy_drinks_rejects()
    test_techno_after_event_old_dislike_rejects_temporal()
    test_dynamic_storytelling_vs_historical_fiction_rejects()
    test_pop_music_meaningful_lyrics_vs_general_music_rejects()
    test_avocado_toast_additions_vs_plain_avocado_toast_rejects()
    test_avoiding_technology_in_travel_vs_cultural_immersion_rejects()
    test_hyderabadi_biryani_vs_generic_biryani_rejects()
    test_science_fiction_ethical_dilemmas_vs_generic_scifi_rejects()
    test_action_movies_unrealistic_science_vs_science_games_rejects()
    test_beach_vacations_over_cultural_trips_vs_adventure_sports_rejects()
    test_solo_strategy_over_multiplayer_vs_generic_strategy_games_rejects()
    test_healthcare_industry_not_user_health_status_rejects()
    test_christopher_dislike_entity_extraction_does_not_swallow_predicate()
