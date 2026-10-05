import { codeExpiresConfiguration } from '@ai-recruit/common';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { User } from 'src/data-access/user';
import { UserConsumer } from './user.consumer';
import { UserController } from './user.controller';
import { UserService } from './user.service';

@Module({
  imports: [
    ConfigModule.forRoot({ load: [codeExpiresConfiguration] }),
    MikroOrmModule.forFeature([User]),
  ],
  controllers: [UserController, UserConsumer],
  providers: [UserService],
  exports: [UserService],
})
export class UserModule {}
