#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# ---------------------------------------------------------------------------##
#
# Copyright (C) 1998-2003 Markus Franz Xaver Johannes Oberhumer
# Copyright (C) 2003 Mt. Hood Playing Card Co.
# Copyright (C) 2005-2009 Skomoroh
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ---------------------------------------------------------------------------##

from pysollib.game import Game
from pysollib.gamedb import GI, GameInfo, registerGame
from pysollib.hint import AbstractHint
from pysollib.layout import Layout
from pysollib.stack import \
        BO_RowStack, \
        DealRowTalonStack, \
        InvisibleStack, \
        RK_FoundationStack, \
        AC_FoundationStack, \
        BO_RowStack, \
        Stack, \
        StackWrapper, \
        WasteStack, \
        WasteTalonStack
from pysollib.util import ACE, KING, QUEEN

# ************************************************************************
# *
# ************************************************************************


class PictureGallery_Hint(AbstractHint):
    def computeHints(self):
        game = self.game

        # 1) try if we can drop a card (i.e. an Ace)
        for r in game.sg.dropstacks:
            t, n = r.canDropCards(game.s.foundations)
            if t and n == 1:
                c = r.getCard()
                assert t is not r and c
                assert c.rank == ACE
                if r in game.s.tableaux:
                    base_score = 90000 + (4 - r.cap.base_rank)
                else:
                    base_score = 90000
                score = base_score + 100 * (self.K - c.rank)
                self.addHint(score, 1, r, t)

        # 2) try if we can move a card to the tableaux
        if not self.hints:
            for r in game.sg.dropstacks:
                pile = r.getPile()
                if not pile or len(pile) != 1:
                    continue
                if r in game.s.tableaux:
                    rr = self.ClonedStack(r, stackcards=r.cards[:-1])
                    if rr.acceptsCards(None, pile):
                        # do not move a card that is already in correct place
                        continue
                    base_score = 80000 + (4 - r.cap.base_rank)
                else:
                    base_score = 80000
                # find a stack that would accept this card
                for t in game.s.tableaux:
                    if t is not r and t.acceptsCards(r, pile):
                        score = base_score + 100 * (self.K - pile[0].rank)
                        self.addHint(score, 1, r, t)
                        break

        # 3) Try if we can move a card from the tableaux
        #    to a row stack. This can only happen if there are
        #    no more cards to deal.
        if not self.hints:
            for r in game.s.tableaux:
                pile = r.getPile()
                if not pile or len(pile) != 1:
                    continue
                rr = self.ClonedStack(r, stackcards=r.cards[:-1])
                if rr.acceptsCards(None, pile):
                    # do not move a card that is already in correct place
                    continue
                # find a stack that would accept this card
                for t in game.s.rows:
                    if t is not r and t.acceptsCards(r, pile):
                        score = 70000 + 100 * (self.K - pile[0].rank)
                        self.addHint(score, 1, r, t)
                        break

        # 4) try if we can move a card within the row stacks
        if not self.hints:
            for r in game.s.rows:
                pile = r.getPile()
                if not pile:
                    continue
                lp = len(pile)
                lr = len(r.cards)
                assert 1 <= lp <= lr
                rpile = r.cards[:(lr-lp)]   # remaining pile
                if not pile or len(pile) != 1 or len(pile) == len(r.cards):
                    continue
                base_score = 60000
                # find a stack that would accept this card
                for t in game.s.rows:
                    if self.shallMovePile(r, t, pile, rpile):
                        score = base_score + 100 * (self.K - pile[0].rank)
                        self.addHint(score, 1, r, t)
                        break

        # 5) try if we can deal cards
        if self.level >= 2:
            if game.canDealCards():
                self.addHint(self.SCORE_DEAL, 0, game.s.talon, None)


# ************************************************************************
# * Picture Gallery
# ************************************************************************

# this Foundation only accepts Aces
class PictureGallery_Foundation(RK_FoundationStack):
    def __init__(self, x, y, game):
        RK_FoundationStack.__init__(
            self, x, y, game, base_rank=ACE, dir=0, max_move=0,
            max_cards=(4 * game.gameinfo.decks))
        self.CARD_YOFFSET = min(30, self.game.app.images.CARD_YOFFSET + 10)

    def getBottomImage(self):
        return self.game.app.images.getLetter(ACE)

    def closeStack(self):
        if len(self.cards) == (4 * self.game.gameinfo.decks):
            if self.game.moves.state not in \
                    (self.game.S_REDO, self.game.S_RESTORE):
                self.game.flipAllMove(self)

    def canFlipCard(self):
        return False


class PictureGallery_TableauStack(BO_RowStack):
    def __init__(self, x, y, game, base_rank, yoffset, dir=3, max_cards=4):
        BO_RowStack.__init__(
            self, x, y, game,
            base_rank=base_rank, dir=dir, max_cards=max_cards, max_accept=1)
        self.CARD_YOFFSET = yoffset

    def acceptsCards(self, from_stack, cards):
        if not BO_RowStack.acceptsCards(self, from_stack, cards):
            return False
        # check that the base card is correct
        if self.cards and self.cards[0].rank != self.cap.base_rank:
            return False
        return True

    getBottomImage = Stack._getLetterImage


class PictureGallery_RowStack(BO_RowStack):
    def acceptsCards(self, from_stack, cards):
        if not BO_RowStack.acceptsCards(self, from_stack, cards):
            return False
        # check
        if self.cards or self.game.s.talon.cards:
            return False
        return True

    getBottomImage = Stack._getTalonBottomImage


# ************************************************************************
# *
# ************************************************************************

class PictureGallery(Game):
    Hint_Class = PictureGallery_Hint

    Foundation_Class = PictureGallery_Foundation
    TableauStack_Classes = [
        StackWrapper(
            PictureGallery_TableauStack, base_rank=3, max_cards=4, dir=3),
        StackWrapper(
            PictureGallery_TableauStack, base_rank=2, max_cards=4, dir=3),
        StackWrapper(
            PictureGallery_TableauStack, base_rank=1, max_cards=4, dir=3),
        ]
    RowStack_Class = StackWrapper(PictureGallery_RowStack, max_accept=1)
    Talon_Class = DealRowTalonStack

    #
    # game layout
    #

    def createGame(self, waste=False, numstacks=8):
        rows = len(self.TableauStack_Classes)
        # create layout
        l, s = Layout(self), self.s
        numtableau = (4 * self.gameinfo.decks)
        TABLEAU_YOFFSET = min(numtableau + 1, max(3, l.YOFFSET // 3))

        # set window
        th = l.YS + ((numtableau + 4) // rows - 1) * TABLEAU_YOFFSET
        # (set piles so that at least 2/3 of a card is visible with 10 cards)
        h = ((numtableau + 2) - 1) * l.YOFFSET + l.CH * 2 // 3
        self.setSize((numtableau + 2) * l.XS + l.XM, l.YM + 3 * th + l.YM + h)

        # create stacks
        s.addattr(tableaux=[])     # register extra stack variable
        x = l.XM + numtableau * l.XS + l.XS // 2
        y = l.YM + l.CH // 2
        s.foundations.append(self.Foundation_Class(x, y, self))
        y = l.YM
        for cl in self.TableauStack_Classes:
            x = l.XM
            for j in range(numtableau):
                s.tableaux.append(cl(x, y, self, yoffset=TABLEAU_YOFFSET))
                x = x + l.XS
            y = y + th
        self.setRegion(s.foundations, (x - l.CW // 2, -999, 999999, y - l.CH))
        x, y = l.XM, y + l.YM
        for i in range(numstacks):
            s.rows.append(self.RowStack_Class(x, y, self))
            x = x + l.XS
        # self.setRegion(s.rows, (-999, -999, x - l.CW // 2, 999999))
        x = l.XM + numstacks * l.XS + l.XS // 2
        y = self.height - l.YS
        s.talon = self.Talon_Class(x, y, self)
        l.createText(s.talon, "se")
        if waste:
            y -= l.YS
            s.waste = WasteStack(x, y, self)
            l.createText(s.waste, "se")

        # define stack-groups
        if waste:
            ws = [s.waste]
        else:
            ws = []
        self.sg.openstacks = s.foundations + s.tableaux + s.rows + ws
        self.sg.talonstacks = [s.talon] + ws
        self.sg.dropstacks = s.tableaux + s.rows + ws

    #
    # game overrides
    #

    def startGame(self):
        self.s.talon.dealRow(rows=self.s.tableaux, frames=0)
        self._startAndDealRow()

    def isGameWon(self):
        if len(self.s.foundations[0].cards) != (4 * self.gameinfo.decks):
            return False
        for stack in self.s.tableaux:
            if len(stack.cards) != 4:
                return False
        return True

    def fillStack(self, stack):
        if self.s.talon.cards:
            if stack in self.s.rows and len(stack.cards) == 0:
                self.s.talon.dealRow(rows=[stack])

    def shallHighlightMatch(self, stack1, card1, stack2, card2):
        if card1.rank == ACE or card2.rank == ACE:
            return False
        return (card1.suit == card2.suit and
                (card1.rank + 3 == card2.rank or card2.rank + 3 == card1.rank))

    def getHighlightPilesStacks(self):
        return ()


class BigPictureGallery(PictureGallery):

    def createGame(self):
        PictureGallery.createGame(self, numstacks=12)


class HugePictureGallery(PictureGallery):

    def createGame(self):
        PictureGallery.createGame(self, numstacks=16)


class SmallPictureGallery(PictureGallery):

    def createGame(self):
        PictureGallery.createGame(self, numstacks=4)


# register the game
registerGame(GameInfo(900047, PictureGallery, "Picture Gallery By Any But Own (Plugin)",
                      GI.GT_2DECK_TYPE, 2, 0, GI.SL_BALANCED))
registerGame(GameInfo(900048, BigPictureGallery, "Big Picture Gallery By Any But Own (Plugin)",
                      GI.GT_3DECK_TYPE, 3, 0, GI.SL_BALANCED))
registerGame(GameInfo(900049, HugePictureGallery, "Huge Picture Gallery By Any But Own (Plugin)",
                      GI.GT_4DECK_TYPE, 4, 0, GI.SL_BALANCED))
registerGame(GameInfo(900040, SmallPictureGallery, "Small Picture Gallery By Any But Own (Plugin)",
                      GI.GT_1DECK_TYPE, 1, 0, GI.SL_BALANCED))
