"""
xnano.ai.models._art_references

The pixel art ArtModel shows as references when a request is close to one of them: small
pieces in the craft the model is asked for, each with its subject and tags.
"""

from __future__ import annotations

from typing import Final

REFERENCES: Final[tuple[dict[str, object], ...]] = (
    {
        'subject': 'a gold coin with a raised inner ring',
        'tags': ['item', 'coin', 'gold', 'money', 'treasure'],
        'width': 8,
        'height': 8,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#fff1c1'},
            'b': {'role': 'base', 'color': '#ffcd75'},
            'd': {'role': 'detail', 'color': '#e39a42'},
            's': {'role': 'shadow', 'color': '#b86f50'},
        },
        'rows': [
            '..oooo..',
            '.ohhbbo.',
            'ohhbbbso',
            'ohbddbso',
            'obbddsso',
            'obbbssso',
            '.obssso.',
            '..oooo..',
        ],
    },
    {
        'subject': 'a red heart with a soft highlight',
        'tags': ['item', 'heart', 'love', 'life', 'health'],
        'width': 8,
        'height': 8,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#f6a5a5'},
            'b': {'role': 'base', 'color': '#b13e53'},
            's': {'role': 'shadow', 'color': '#73275c'},
        },
        'rows': [
            '.oo..oo.',
            'ohboobso',
            'ohbbbbso',
            'obbbbsso',
            'obbbssso',
            '.obssso.',
            '..osso..',
            '...oo...',
        ],
    },
    {
        'subject': 'a brass key with a round bow',
        'tags': ['item', 'key', 'unlock', 'door', 'treasure'],
        'width': 8,
        'height': 8,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#fff1c1'},
            'b': {'role': 'base', 'color': '#ffcd75'},
            's': {'role': 'shadow', 'color': '#b86f50'},
        },
        'rows': [
            '..oooo..',
            '.ohhbbo.',
            '.ohoobo.',
            '.obooso.',
            '.obbsso.',
            '..obso..',
            '..obbbo.',
            '..ooooo.',
        ],
    },
    {
        'subject': 'a green slime with two dark eyes',
        'tags': ['character', 'slime', 'monster', 'blob', 'enemy'],
        'width': 8,
        'height': 8,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#a7f070'},
            'b': {'role': 'base', 'color': '#38b764'},
            's': {'role': 'shadow', 'color': '#257179'},
            'd': {'role': 'detail', 'color': '#29366f'},
        },
        'rows': [
            '........',
            '..ooooo.',
            '.ohhbbbo',
            'ohdbbdso',
            'obbbbbso',
            'obbbssso',
            '.obssso.',
            '..oooo..',
        ],
    },
    {
        'subject': 'a red mushroom with white spots',
        'tags': ['nature', 'mushroom', 'forest', 'toadstool', 'plant'],
        'width': 8,
        'height': 8,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'd': {'role': 'detail', 'color': '#f4f4f4'},
            'b': {'role': 'base', 'color': '#b13e53'},
            's': {'role': 'shadow', 'color': '#73275c'},
            'k': {'role': 'skin', 'color': '#f4e2c2'},
        },
        'rows': [
            '..oooo..',
            '.odbbbo.',
            'obdbbdso',
            'obbbbsso',
            'oooooooo',
            '..okkko.',
            '..okkko.',
            '..ooooo.',
        ],
    },
    {
        'subject': 'a yellow lightning bolt',
        'tags': ['icon', 'lightning', 'bolt', 'energy', 'power', 'storm'],
        'width': 8,
        'height': 8,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#fff1c1'},
            'b': {'role': 'base', 'color': '#ffcd75'},
            's': {'role': 'shadow', 'color': '#ef7d57'},
        },
        'rows': [
            '...oooo.',
            '..ohhbo.',
            '.ohbbo..',
            'ohbboooo',
            'ooobbbso',
            '...obso.',
            '..obso..',
            '.oooo...',
        ],
    },
    {
        'subject': 'a glass potion bottle with red liquid and a cork',
        'tags': ['item', 'potion', 'bottle', 'health', 'flask', 'magic'],
        'width': 12,
        'height': 12,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'k': {'role': 'skin', 'color': '#a77b5b'},
            'h': {'role': 'highlight', 'color': '#f4f4f4'},
            'b': {'role': 'base', 'color': '#94b0c2'},
            's': {'role': 'shadow', 'color': '#566c86'},
            'a': {'role': 'accent', 'color': '#b13e53'},
            'd': {'role': 'detail', 'color': '#73275c'},
        },
        'rows': [
            '....oooo....',
            '....okkko...',
            '....okkko...',
            '....ohbso...',
            '...ohbbbso..',
            '..ohbbbbbso.',
            '.ohbaaaaabso',
            '.ohahaaaadso',
            '.obaaaaaddso',
            '.obaaaadddso',
            '..osdddddso.',
            '...oooooooo.',
        ],
    },
    {
        'subject': 'a steel sword with a gold crossguard',
        'tags': ['item', 'sword', 'weapon', 'blade', 'knight'],
        'width': 12,
        'height': 12,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'b': {'role': 'base', 'color': '#94b0c2'},
            'h': {'role': 'highlight', 'color': '#f4f4f4'},
            's': {'role': 'shadow', 'color': '#566c86'},
            'a': {'role': 'accent', 'color': '#ffcd75'},
            'd': {'role': 'detail', 'color': '#b86f50'},
            'k': {'role': 'skin', 'color': '#73275c'},
        },
        'rows': [
            '.....o......',
            '....obo.....',
            '...ohbso....',
            '...ohbso....',
            '...ohbso....',
            '...ohbso....',
            '.oooooooooo.',
            'ohaaaaaaaddo',
            '.ooookkoooo.',
            '....okko....',
            '...oaaddo...',
            '...oooooo...',
        ],
    },
    {
        'subject': 'an orange cat sitting and facing forward',
        'tags': ['character', 'cat', 'pet', 'animal', 'kitten'],
        'width': 12,
        'height': 12,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#ffcd75'},
            'b': {'role': 'base', 'color': '#ef7d57'},
            's': {'role': 'shadow', 'color': '#b86f50'},
            'd': {'role': 'detail', 'color': '#38b764'},
            'a': {'role': 'accent', 'color': '#f6a5a5'},
            'k': {'role': 'skin', 'color': '#f4f4f4'},
        },
        'rows': [
            '.oo....oo...',
            '.oaooooao...',
            'ohbbbbbbso..',
            'ohbdbbdbso..',
            'obbkakbbso..',
            '.obkkkkso...',
            'ohbkkkkbso..',
            'ohbkkkkbsooo',
            'obbkkkkbsobo',
            'obbbbbbbsobo',
            'okbbbbbksobo',
            'oooooooooooo',
        ],
    },
    {
        'subject': 'a pink flower with a yellow centre and a leaf',
        'tags': ['nature', 'flower', 'daisy', 'garden', 'plant', 'spring'],
        'width': 12,
        'height': 12,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#fbd3e0'},
            'b': {'role': 'base', 'color': '#f6a5a5'},
            's': {'role': 'shadow', 'color': '#b13e53'},
            'a': {'role': 'accent', 'color': '#ffcd75'},
            'd': {'role': 'detail', 'color': '#e39a42'},
            'l': {'role': 'detail', 'color': '#38b764'},
        },
        'rows': [
            '...oooooo...',
            '.oohhbbbsoo.',
            '.ohhboooobso',
            'ohhboaadobso',
            'ohbboaddobso',
            'obbboooobsso',
            '.obbbbbsssso',
            '..obbssssoo.',
            '...oooloo...',
            '..oooolo....',
            '..ollllo....',
            '..oooooo....',
        ],
    },
    {
        'subject': 'a grey gear with eight teeth and a hole in the middle',
        'tags': ['icon', 'gear', 'settings', 'cog', 'machine'],
        'width': 12,
        'height': 12,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#f4f4f4'},
            'b': {'role': 'base', 'color': '#94b0c2'},
            's': {'role': 'shadow', 'color': '#566c86'},
        },
        'rows': [
            '....oooo....',
            '.oo.ohbo.oo.',
            '.ohoohbboso.',
            '.ohhhbbbbsso',
            'oohhoooobsoo',
            'ohhho..obbso',
            'ohbbo..obsso',
            'oobboooossoo',
            '.obbbbbsssso',
            '.oboobssoso.',
            '.oo.obso.oo.',
            '....oooo....',
        ],
    },
    {
        'subject': 'a bone-white skull with dark eye sockets',
        'tags': ['icon', 'skull', 'death', 'danger', 'bones', 'pirate'],
        'width': 12,
        'height': 12,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#ffffff'},
            'b': {'role': 'base', 'color': '#e8e8e8'},
            's': {'role': 'shadow', 'color': '#94b0c2'},
            'd': {'role': 'detail', 'color': '#333c57'},
        },
        'rows': [
            '...oooooo...',
            '.oohhbbbboo.',
            '.ohhbbbbbbso',
            'ohhbbbbbbbso',
            'ohbddbbddbso',
            'obbddbbddsso',
            'obbbbddbbsso',
            '.obbbbbbbsso',
            '..oobbbbsoo.',
            '...obdbdbo..',
            '...obdbdbo..',
            '...oooooo...',
        ],
    },
    {
        'subject': 'a knight in steel armor with a red plume and a shield',
        'tags': ['character', 'knight', 'armor', 'medieval', 'warrior', 'shield'],
        'width': 16,
        'height': 16,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'b': {'role': 'base', 'color': '#94b0c2'},
            's': {'role': 'shadow', 'color': '#566c86'},
            'h': {'role': 'highlight', 'color': '#f4f4f4'},
            'r': {'role': 'accent', 'color': '#b13e53'},
            'd': {'role': 'detail', 'color': '#73275c'},
            'y': {'role': 'detail', 'color': '#ffcd75'},
        },
        'rows': [
            '......oooo......',
            '.....orrrdo.....',
            '....oorrrdoo....',
            '...ohhbbbbbso...',
            '..ohhbbbbbbsso..',
            '..ohbbbbbbbsso..',
            '..oooooooooooo..',
            '..obssssssssso..',
            '..obbbbbbbbsso..',
            '.oooobbbbbsoooo.',
            'ohbbbbbbbbsbsso.',
            'oooobbbbbbsobso.',
            'ohrrobbbbbsobso.',
            'ohryrobbbbsobso.',
            'obrrsobbobsoooo.',
            '.ooooooooooo....',
        ],
    },
    {
        'subject': 'a wizard with a tall blue hat, a white beard and a staff',
        'tags': ['character', 'wizard', 'mage', 'magic', 'staff', 'fantasy'],
        'width': 16,
        'height': 16,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'b': {'role': 'base', 'color': '#3b5dc9'},
            's': {'role': 'shadow', 'color': '#29366f'},
            'h': {'role': 'highlight', 'color': '#41a6f6'},
            'k': {'role': 'skin', 'color': '#e8b796'},
            'w': {'role': 'detail', 'color': '#f4f4f4'},
            'y': {'role': 'detail', 'color': '#ffcd75'},
            'd': {'role': 'detail', 'color': '#a77b5b'},
        },
        'rows': [
            '.......oo.......',
            '......ohso......',
            '......ohbso..ooo',
            '.....ohhbbso.oyo',
            '....ohhbbbso.oyo',
            '...ohhbbybssoodo',
            '.ooooooooooooodo',
            '..okkokkokko.odo',
            '..okkkkkkkko.odo',
            '.oowwwwwwwwooodo',
            'ohbbwwwwwwssoodo',
            'ohbbbwwwwbsskodo',
            'ohbbbbwwbbsskodo',
            'ohbbbbbbbbssoodo',
            'obbbbbbbbbssoodo',
            'oooooooooooooooo',
        ],
    },
    {
        'subject': 'a wooden treasure chest with gold bands and a lock',
        'tags': ['item', 'chest', 'treasure', 'loot', 'wood', 'gold'],
        'width': 16,
        'height': 16,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#e0a070'},
            'b': {'role': 'base', 'color': '#b86f50'},
            's': {'role': 'shadow', 'color': '#7a4432'},
            'y': {'role': 'detail', 'color': '#ffcd75'},
            'd': {'role': 'detail', 'color': '#c9962f'},
            'l': {'role': 'detail', 'color': '#566c86'},
        },
        'rows': [
            '...oooooooooo...',
            '.oohhbbbbbbbsoo.',
            'ohhbbbbbbbbbbsso',
            'oyyyyyyyyyyyyddo',
            'ohbybbbbbbbbysso',
            'ohbybbbbbbbbysso',
            'oooooooooooooooo',
            'oyyyyyoooooyyydo',
            'ohbybbolllobysso',
            'ohbybbololobysso',
            'obbybbooooobysso',
            'obbybbbbbbbbysso',
            'obbybbbbbbbbysso',
            'oyyyyyyyyyyyyddo',
            'obbybbbbbbbbysso',
            'oooooooooooooooo',
        ],
    },
    {
        'subject': 'a round green tree with red apples',
        'tags': ['nature', 'tree', 'forest', 'apple', 'plant', 'oak'],
        'width': 16,
        'height': 16,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'b': {'role': 'base', 'color': '#38b764'},
            's': {'role': 'shadow', 'color': '#257179'},
            'h': {'role': 'highlight', 'color': '#a7f070'},
            'r': {'role': 'accent', 'color': '#b13e53'},
            't': {'role': 'detail', 'color': '#8b5a3c'},
            'd': {'role': 'detail', 'color': '#5c3a24'},
        },
        'rows': [
            '.....oooooo.....',
            '...oohhbbbsoo...',
            '..ohhhbbbbbsso..',
            '.ohhhbbbbbbbsso.',
            'ohhbbbrbbbbbssso',
            'ohbbbbbbbbrbssso',
            'obbbrbbbbbbbssso',
            'obbbbbbbbbbsssso',
            '.obbbbbrbbssssso',
            '..obbbbbbsssssso',
            '...ooottddooooo.',
            '.....ottddo.....',
            '.....ottddo.....',
            '.....ottddo.....',
            '....otttdddo....',
            '....oooooooo....',
        ],
    },
    {
        'subject': 'a cottage with a red roof, a chimney and lit windows',
        'tags': ['icon', 'house', 'home', 'cottage', 'building', 'village'],
        'width': 16,
        'height': 16,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#f6757a'},
            'r': {'role': 'accent', 'color': '#b13e53'},
            'd': {'role': 'detail', 'color': '#73275c'},
            's': {'role': 'shadow', 'color': '#c9b48c'},
            'b': {'role': 'base', 'color': '#f4e2c2'},
            't': {'role': 'detail', 'color': '#8b5a3c'},
            'y': {'role': 'detail', 'color': '#ffcd75'},
        },
        'rows': [
            '...........ooo..',
            '.......oo..oso..',
            '......ohdo.oso..',
            '.....ohrrdooso..',
            '....ohrrrrdooo..',
            '...ohrrrrrrddo..',
            '..ohrrrrrrrrddo.',
            '.ohrrrrrrrrrrddo',
            'oooooooooooooooo',
            'obbbbbbbbbbbbsso',
            'oooooboooobooooo',
            'ooyyobottoboyyoo',
            'ooyyobotyoboyyoo',
            'ooooobottobooooo',
            'obbbbbottobbbbso',
            'oooooooooooooooo',
        ],
    },
    {
        'subject': 'a rocket with a red nose cone, fins and a flame',
        'tags': ['icon', 'rocket', 'space', 'launch', 'ship', 'startup'],
        'width': 16,
        'height': 16,
        'palette': {
            'o': {'role': 'outline', 'color': '#1a1c2c'},
            'h': {'role': 'highlight', 'color': '#ffffff'},
            'r': {'role': 'accent', 'color': '#b13e53'},
            'd': {'role': 'detail', 'color': '#73275c'},
            'b': {'role': 'base', 'color': '#dde4ea'},
            's': {'role': 'shadow', 'color': '#94b0c2'},
            'w': {'role': 'detail', 'color': '#41a6f6'},
            'y': {'role': 'detail', 'color': '#ffcd75'},
            'f': {'role': 'accent', 'color': '#ef7d57'},
        },
        'rows': [
            '.......oo.......',
            '......ohro......',
            '.....ohrrdo.....',
            '.....ohrrdo.....',
            '.....oooooo.....',
            '.....ohbbso.....',
            '.....ohwwso.....',
            '.....ohwwso.....',
            '....oohbbsoo....',
            '...orohbbsodo...',
            '..orrohbbsoddo..',
            '.orrrohbbsodddo.',
            '.ooooossssooooo.',
            '.....oyyffo.....',
            '......oyfo......',
            '.......oo.......',
        ],
    },
    {
        'subject': 'a young woman with long brown hair, head and shoulders',
        'tags': [
            'portrait',
            'face',
            'head',
            'woman',
            'girl',
            'lady',
            'female',
            'person',
            'hair',
            'bust',
            'avatar',
            'character',
            'human',
        ],
        'width': 20,
        'height': 24,
        'palette': {
            'o': {'role': 'outline', 'color': '#2b1d2e'},
            'h': {'role': 'base', 'color': '#8b5a3c'},
            'l': {'role': 'highlight', 'color': '#b98356'},
            'd': {'role': 'shadow', 'color': '#5e3a26'},
            's': {'role': 'skin', 'color': '#f2cfb3'},
            't': {'role': 'shadow', 'color': '#d7a380'},
            'e': {'role': 'detail', 'color': '#fbf6ef'},
            'i': {'role': 'detail', 'color': '#2b1d2e'},
            'm': {'role': 'accent', 'color': '#c9566d'},
            'c': {'role': 'base', 'color': '#4f7f9c'},
            'k': {'role': 'shadow', 'color': '#365a71'},
        },
        'rows': [
            '.......oooooo.......',
            '......ohhhhhho......',
            '.....ohlllhhddo.....',
            '....olllhhhhhhdo....',
            '...ollhhhhhhhhdho...',
            '..ohllhhhhhhhhhdho..',
            '..ohhhhhsssshhhdho..',
            '..ohhhsssssssshddo..',
            '..ohhhiissssiihddo..',
            '..ohlseissssiesddo..',
            '..ohlssssssssssddo..',
            '..ohlssssttssssddo..',
            '..ohlssssssssssddo..',
            '..ohlhssmmmmsshddo..',
            '..ohhhossssssohdho..',
            '..ohhhottttttoddho..',
            '..ohhhoottttooddho..',
            '..ohhhoottttooddho..',
            '...ohhoottttoohho...',
            '..ooccckkkkkkcccoo..',
            '.occcccckkkkcccccco.',
            '.occcccccccccccccco.',
            'occcccccccccccccccco',
            'occcccccccccccccccco',
        ],
        'svg': (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 24">\n'
            '<!-- the masses, back to front, each outlined by a stroke under its fill -->\n'
            '<g stroke="o" stroke-width="2" paint-order="stroke">\n'
            '  <ellipse cx="10" cy="8" rx="7" ry="7" fill="h"/>\n'
            '  <rect x="3" y="8" width="3" height="11" fill="h"/>\n'
            '  <rect x="14" y="8" width="3" height="11" fill="h"/>\n'
            '  <rect x="8" y="14" width="4" height="6" fill="t"/>\n'
            '  <path d="M4 19H16V20H18V22H19V24H1V22H2V20H4Z" fill="c"/>\n'
            '  <ellipse cx="10" cy="10" rx="5" ry="6" fill="s"/>\n'
            '</g>\n'
            '<!-- the fringe, parted in the middle -->\n'
            '<path d="M5 4H15V6H12V7H8V6H5Z" fill="h"/>\n'
            '<!-- light from the top left: a highlight, and shadow on the right -->\n'
            '<rect x="6" y="2" width="4" height="1" fill="l"/>\n'
            '<rect x="4" y="4" width="2" height="2" fill="l"/>\n'
            '<rect x="4" y="9" width="1" height="5" fill="l"/>\n'
            '<rect x="15" y="5" width="1" height="10" fill="d"/>\n'
            '<rect x="16" y="7" width="1" height="7" fill="d"/>\n'
            '<!-- the collar -->\n'
            '<path d="M7 19H13V20H12V21H8V20H7Z" fill="k"/>\n'
            '<!-- eyes: a lash line over a white and a dark iris -->\n'
            '<rect x="6" y="8" width="2" height="1" fill="i"/>\n'
            '<rect x="12" y="8" width="2" height="1" fill="i"/>\n'
            '<rect x="6" y="9" width="1" height="1" fill="e"/>\n'
            '<rect x="7" y="9" width="1" height="1" fill="i"/>\n'
            '<rect x="12" y="9" width="1" height="1" fill="i"/>\n'
            '<rect x="13" y="9" width="1" height="1" fill="e"/>\n'
            '<!-- nose, mouth, and the shadow under the chin -->\n'
            '<rect x="9" y="11" width="2" height="1" fill="t"/>\n'
            '<rect x="8" y="13" width="4" height="1" fill="m"/>\n'
            '</svg>\n'
        ),
        'program': (
            '# hair behind the head, falling to the shoulders\n'
            "ellipse(3, 1, 14, 14, 'h')\n"
            "rect(3, 8, 3, 10, 'h')\n"
            "rect(4, 18, 2, 1, 'h')\n"
            '# neck, then the shoulders\n'
            "rect(8, 14, 4, 5, 't')\n"
            "rect(4, 19, 12, 5, 'c')\n"
            "rect(2, 20, 16, 4, 'c')\n"
            "rect(1, 22, 18, 2, 'c')\n"
            '# the face\n'
            "ellipse(5, 4, 10, 12, 's')\n"
            'mirror_x()\n'
            "outline('o')\n"
            '# the fringe, parted in the middle\n'
            "rect(5, 4, 10, 2, 'h')\n"
            "rect(5, 6, 3, 1, 'h')\n"
            "rect(12, 6, 3, 1, 'h')\n"
            "rect(5, 7, 1, 2, 'h')\n"
            "rect(14, 7, 1, 2, 'h')\n"
            '# light from the top left: hair highlight, and shadow on the right\n'
            "rect(7, 2, 3, 1, 'l')\n"
            "rect(5, 3, 3, 1, 'l')\n"
            "rect(4, 4, 2, 2, 'l')\n"
            "rect(4, 9, 1, 5, 'l')\n"
            "rect(12, 2, 2, 1, 'd')\n"
            "rect(14, 3, 1, 2, 'd')\n"
            "rect(15, 5, 1, 10, 'd')\n"
            "rect(16, 7, 1, 7, 'd')\n"
            "rect(14, 15, 2, 3, 'd')\n"
            '# the collar\n'
            "rect(7, 19, 6, 1, 'k')\n"
            "rect(8, 20, 4, 1, 'k')\n"
            '# eyes: a lash line over a white and a dark iris\n'
            "rect(6, 8, 2, 1, 'i')\n"
            "pixel(6, 9, 'e')\n"
            "pixel(7, 9, 'i')\n"
            "rect(12, 8, 2, 1, 'i')\n"
            "pixel(12, 9, 'i')\n"
            "pixel(13, 9, 'e')\n"
            '# nose, mouth, and the shadow under the chin\n'
            "rect(9, 11, 2, 1, 't')\n"
            "rect(8, 13, 4, 1, 'm')\n"
            "rect(7, 15, 6, 1, 't')\n"
        ),
    },
    {
        'subject': 'a man with short dark hair and a beard, head and shoulders',
        'tags': [
            'portrait',
            'face',
            'head',
            'man',
            'guy',
            'male',
            'person',
            'beard',
            'bust',
            'avatar',
            'character',
            'human',
        ],
        'width': 20,
        'height': 24,
        'palette': {
            'o': {'role': 'outline', 'color': '#2b1d2e'},
            'h': {'role': 'base', 'color': '#3b2a28'},
            'l': {'role': 'highlight', 'color': '#5a4542'},
            'd': {'role': 'shadow', 'color': '#241716'},
            's': {'role': 'skin', 'color': '#f2cfb3'},
            't': {'role': 'shadow', 'color': '#d7a380'},
            'e': {'role': 'detail', 'color': '#fbf6ef'},
            'i': {'role': 'detail', 'color': '#2b1d2e'},
            'm': {'role': 'accent', 'color': '#c9566d'},
            'c': {'role': 'base', 'color': '#6f8f5a'},
            'k': {'role': 'shadow', 'color': '#4d6a3e'},
        },
        'rows': [
            '........oooo........',
            '......oohhhhoo......',
            '.....ohlllhhddo.....',
            '....olllhhhhhhdo....',
            '...ohhhhhhhhhhdho...',
            '...ohhhhhhhhhhdho...',
            '...ohhhsssssshhho...',
            '...ohhddssssddhho...',
            '...ohhsssssssshho...',
            '...otseissssiesto...',
            '...otssssssssssto...',
            '...otssssttssssto...',
            '....ossshhhhssso....',
            '.....ohhhmmhhho.....',
            '......hhhhhhhd......',
            '.......hhhhhh.......',
            '.......otttto.......',
            '.......otttto.......',
            '....oooottttoooo....',
            '..ooccckkkkkkcccoo..',
            '.occcccckkkkcccccco.',
            '.occcccccccccccccco.',
            'occcccccccccccccccco',
            'occcccccccccccccccco',
        ],
        'svg': (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 24">\n'
            '<!-- the masses, back to front, each outlined by a stroke under its fill -->\n'
            '<g stroke="o" stroke-width="2" paint-order="stroke">\n'
            '  <ellipse cx="10" cy="6.5" rx="6" ry="5.5" fill="h"/>\n'
            '  <rect x="8" y="14" width="4" height="6" fill="t"/>\n'
            '  <path d="M4 19H16V20H18V22H19V24H1V22H2V20H4Z" fill="c"/>\n'
            '  <rect x="4" y="9" width="12" height="3" fill="t"/>\n'
            '  <ellipse cx="10" cy="10" rx="5" ry="6" fill="s"/>\n'
            '</g>\n'
            '<!-- the hairline, and the beard along the jaw -->\n'
            '<path d="M5 4H15V6H13V7H14V9H13V7H7V9H6V7H7V6H5Z" fill="h"/>\n'
            '<path d="M8 12H12V13H14V15H13V16H7V15H6V13H8Z" fill="h"/>\n'
            '<!-- light from the top left, shadow on the right -->\n'
            '<rect x="7" y="2" width="3" height="1" fill="l"/>\n'
            '<rect x="5" y="3" width="3" height="1" fill="l"/>\n'
            '<rect x="12" y="2" width="2" height="1" fill="d"/>\n'
            '<rect x="14" y="3" width="1" height="3" fill="d"/>\n'
            '<rect x="13" y="14" width="1" height="1" fill="d"/>\n'
            '<!-- the collar -->\n'
            '<path d="M7 19H13V20H12V21H8V20H7Z" fill="k"/>\n'
            '<!-- brows and eyes -->\n'
            '<rect x="6" y="7" width="2" height="1" fill="d"/>\n'
            '<rect x="12" y="7" width="2" height="1" fill="d"/>\n'
            '<rect x="6" y="9" width="1" height="1" fill="e"/>\n'
            '<rect x="7" y="9" width="1" height="1" fill="i"/>\n'
            '<rect x="12" y="9" width="1" height="1" fill="i"/>\n'
            '<rect x="13" y="9" width="1" height="1" fill="e"/>\n'
            '<!-- nose and mouth -->\n'
            '<rect x="9" y="11" width="2" height="1" fill="t"/>\n'
            '<rect x="9" y="13" width="2" height="1" fill="m"/>\n'
            '</svg>\n'
        ),
        'program': (
            '# short hair close to the head\n'
            "ellipse(4, 1, 12, 11, 'h')\n"
            '# neck, then the shoulders\n'
            "rect(8, 14, 4, 5, 't')\n"
            "rect(4, 19, 12, 5, 'c')\n"
            "rect(2, 20, 16, 4, 'c')\n"
            "rect(1, 22, 18, 2, 'c')\n"
            '# the face, and the ears\n'
            "ellipse(5, 4, 10, 12, 's')\n"
            "rect(4, 9, 1, 3, 't')\n"
            'mirror_x()\n'
            "outline('o')\n"
            '# the hairline, and the beard along the jaw\n'
            "rect(5, 4, 10, 2, 'h')\n"
            "rect(5, 6, 2, 1, 'h')\n"
            "rect(13, 6, 2, 1, 'h')\n"
            "rect(5, 7, 1, 2, 'h')\n"
            "rect(14, 7, 1, 2, 'h')\n"
            "rect(6, 13, 8, 2, 'h')\n"
            "rect(7, 15, 6, 1, 'h')\n"
            "rect(8, 12, 4, 1, 'h')\n"
            '# light from the top left\n'
            "rect(7, 2, 3, 1, 'l')\n"
            "rect(5, 3, 3, 1, 'l')\n"
            "rect(12, 2, 2, 1, 'd')\n"
            "rect(14, 3, 1, 3, 'd')\n"
            "rect(13, 14, 1, 1, 'd')\n"
            '# the collar\n'
            "rect(7, 19, 6, 1, 'k')\n"
            "rect(8, 20, 4, 1, 'k')\n"
            '# brows and eyes\n'
            "rect(6, 7, 2, 1, 'd')\n"
            "rect(12, 7, 2, 1, 'd')\n"
            "pixel(6, 9, 'e')\n"
            "pixel(7, 9, 'i')\n"
            "pixel(12, 9, 'i')\n"
            "pixel(13, 9, 'e')\n"
            '# nose and mouth\n'
            "rect(9, 11, 2, 1, 't')\n"
            "rect(9, 13, 2, 1, 'm')\n"
        ),
    },
)
"""Every built-in reference, in the order of the library."""
