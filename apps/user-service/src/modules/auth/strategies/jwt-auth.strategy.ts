import {
  ERROR_RESPONSE,
  jwtConfiguration,
  JwtTokenType,
  ServerException,
} from '@app/common';
import { UserRequestPayload } from '@app/common';
import { RedisService } from '@app/core';
import { Inject, Injectable } from '@nestjs/common';
import { ConfigType } from '@nestjs/config';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { UserRepository } from '../../../data-access/user';

@Injectable()
export class JwtAuthStrategy extends PassportStrategy(Strategy, 'jwt-auth') {
  constructor(
    private redisService: RedisService,
    @Inject(jwtConfiguration.KEY)
    private jwtConfig: ConfigType<typeof jwtConfiguration>,
    private readonly userRepo: UserRepository,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: jwtConfig.secret,
    });
  }

  async validate(payload: any): Promise<UserRequestPayload> {
    const { id, email, jti, type, role } = payload;
    if (type !== JwtTokenType.AccessToken)
      throw new ServerException(ERROR_RESPONSE.UNAUTHORIZED);

    // Check valid token
    const userTokenKey = this.redisService.getUserTokenKey(id, jti);
    const isTokenValid = await this.redisService.getValue<string>(userTokenKey);
    if (!isTokenValid) throw new ServerException(ERROR_RESPONSE.UNAUTHORIZED);

    const user = await this.userRepo.findOne({ id });
    if (!user) throw new ServerException(ERROR_RESPONSE.USER_NOT_FOUND);
    if (!user.isActive) throw new ServerException(ERROR_RESPONSE.USER_DEACTIVATED);

    return {
      id,
      email,
      jti,
      role,
      emailVerified: true,
    };
  }
}
