import { MapSchema, Schema, type } from '@colyseus/schema';

export class PlayerState extends Schema {
  @type('string') id = '';
  @type('string') nickname = '';
  @type('string') team = '';
  @type('number') x = 0;
  @type('number') y = 0;
  @type('string') status = 'free';
  @type('number') kills = 0;
  @type('number') deaths = 0;
  @type('number') captures = 0;
  @type('boolean') connected = true;
  @type('boolean') bot = false;
  @type('number') slot = 0;
  @type('number') tagReadyAt = 0;
}

export class FlagState extends Schema {
  @type('string') owner = '';
  @type('number') x = 0;
  @type('number') y = 0;
  @type('string') status = 'home';
  @type('string') carrierId = '';
}

export class GameState extends Schema {
  @type({map: PlayerState}) players = new MapSchema<PlayerState>();
  @type({map: FlagState}) flags = new MapSchema<FlagState>();
  @type('string') phase = 'lobby';
  @type('number') round = 1;
  @type('number') targetScore = 5;
  @type('number') northScore = 0;
  @type('number') southScore = 0;
  @type('string') hostId = '';
  @type('boolean') practice = false;
  @type('number') serverTime = 0;
  @type('number') phaseEndsAt = 0;
  @type('string') lastPointWinner = '';
  @type('string') lastPointReason = '';
  @type('string') endReason = '';
}
