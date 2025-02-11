import dh3
import pyspiel
import numpy as np
import time
import random 

random.seed(123)
np.random.seed(123)
def to_bool(x):
    if isinstance(x, list):
        x = np.array(x)
    if x.dtype == bool:
        return x
    return x != 0

# games to test (compare openspiel implementation with dh3 implementation)
GAMES = {
    'Classical Phantom Tic-Tac-Toe': (
        pyspiel.load_game('phantom_ttt(obstype=reveal-nothing)'),
        dh3.PtttState
    ),
    'Abrupt Phantom Tic-Tac-Toe': (
        pyspiel.load_game('phantom_ttt(obstype=reveal-nothing,gameversion=abrupt)'),
        dh3.AbruptPtttState
    ),
    'Classical 3x3 Dark Hex': (
        pyspiel.load_game('dark_hex(board_size=3,gameversion=cdh,obstype=reveal-nothing)'),
        dh3.DhState
    ),
    'Abrupt 3x3 Dark Hex': (
        pyspiel.load_game('dark_hex(board_size=3,gameversion=adh,obstype=reveal-nothing)'),
        dh3.AbruptDhState
    ),
}

# compare information state sizes
print('Information state sizes')
for game_str, (os_game, dh3_state_fn) in GAMES.items():
    os_tensor = os_game.new_initial_state().information_state_tensor()
    dh_tensor = dh3_state_fn().compute_openspiel_infostate()
    print(f'- {game_str}: Open Spiel = {len(os_tensor)}, DH3 = {len(dh_tensor)}')
print()

# number of random runs for each game
N = 10_000
actions_history = np.zeros(100, dtype=np.int32) - 1  # save actions for debugging
for game_str, (os_game, dh3_state_fn) in GAMES.items():
    print(f'Testing {game_str} over {N} random games')
    t0 = time.time()
    for i in range(1, N+1):
        try:
            actions_history[:] = -1
            if i % 100_000 == 0:
                t_elapsed = time.time() - t0
                t_remaining = (N - i) * t_elapsed / i
                print(f'{i}/{N} ; {t_elapsed/60:.1f}min elapsed ; {t_remaining/60:.1f}min remaining')
            # new initial state
            os_state = os_game.new_initial_state()
            dh3_state = dh3_state_fn()
            # game loop
            t = 0
            while True:
                # get is terminal
                os_terminal = os_state.is_terminal()
                dh3_terminal = dh3_state.is_terminal()
                assert os_terminal == dh3_terminal, 'terminal'
                if os_terminal or dh3_terminal:
                    break
                # get current player
                os_player = os_state.current_player()
                dh3_player = dh3_state.player()
                assert os_player == dh3_player, 'player'
                # get legal actions
                oh_legal_actions = os_state.legal_actions()
                dh3_legal_actions = [i for (i, x) in enumerate(dh3_state.action_mask()) if x]
                assert oh_legal_actions == dh3_legal_actions, 'legal_actions'

                os_ist = to_bool(os_state.information_state_tensor())
                dh_ist = to_bool(dh3_state.compute_openspiel_infostate())
                assert (os_ist == dh_ist).all(), 'information_state_tensor'
                
                # sample random action
                action = np.random.choice(oh_legal_actions)
                actions_history[t] = action
                # apply action
                os_state.apply_action(action)
                dh3_state.next(action)
                t += 1
            # get winner
            os_rewards = os_state.rewards()
            os_winner = 0 if os_rewards[0] > 0.5 else 1 if os_rewards[0] < -0.5 else None
            dh3_winner = dh3_state.winner()
            assert os_winner == dh3_winner, 'winner'
        except AssertionError as e:
            print(f'Error on game {game_str} with actions {actions_history}: {e}')
    print()
