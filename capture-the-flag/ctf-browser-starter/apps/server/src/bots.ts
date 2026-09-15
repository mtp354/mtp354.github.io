import { canTag, center, distance, isSafe, opposite, type Config, type Input, type Match, type Player, type Point } from '@ctf/rules';

/** A deliberately simple practice opponent: the same intents and rules as humans. */
export function botInput(match: Match, player: Player, slot: number, config: Config): Input {
  const idle = {sequence: 0, moveX: 0, moveY: 0, tag: false};
  if (player.status !== 'free' || match.phase !== 'playing') return idle;
  const enemyFlag = match.flags[opposite(player.team)];
  const ownFlag = match.flags[player.team];
  const enemies = match.players.filter(p => p.team !== player.team && p.status === 'free');
  const byDistance = (a: Player, b: Player) => distance(player, a) - distance(player, b) || a.id.localeCompare(b.id);
  const invader = enemies.filter(p => !isSafe(p, config)).sort(byDistance)[0];
  const teammateNeedsRescue = match.players.some(p => p.team === player.team && p.status === 'jailed');
  let destination: Point;
  if (enemyFlag.carrierId === player.id) {
    destination = config.spawn[player.team];
  } else if (teammateNeedsRescue) {
    destination = center(config.jail[opposite(player.team)]);
  } else if (invader && (slot === 1 || ownFlag.carrierId === invader.id || distance(player, invader) < 450)) {
    destination = invader;
  } else if (slot === 1) {
    // One South defender makes stealing a flag meaningful without chasing across safety.
    destination = {x: config.flagHome[player.team].x + 400, y: config.flagHome[player.team].y + 550};
  } else {
    destination = enemyFlag;
    // Give attacking bots a visible flanking route and avoid endlessly meeting head-on.
    const lane = slot % 2 === 0 ? 1200 : -800;
    if (Math.abs(player.y - destination.y) > 1100) destination = {x: lane, y: destination.y};
  }
  const dx = destination.x - player.x;
  const dy = destination.y - player.y;
  const length = Math.hypot(dx, dy);
  return {
    sequence: 0,
    moveX: length > 20 ? dx / length : 0,
    moveY: length > 20 ? dy / length : 0,
    tag: enemies.some(enemy => canTag(player, enemy, config)),
  };
}
