import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View
import asyncio
import time
import os

from dbmanager import DatabaseManager

class Study(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_manager = DatabaseManager("study_sessions.db")
        self.db_manager.create_tables()
        
        # Dictionary to track active study sessions
        # Format: {server_id: {
        #   'session_id': int, 
        #   'participants': set(user_ids), 
        #   'start_time': timestamp, 
        #   'channel_id': int,
        #   'pomodoro': {
        #     'enabled': bool,
        #     'work_duration': int (minutes),
        #     'break_duration': int (minutes),
        #     'current_phase': 'work'|'break',
        #     'phase_start': timestamp,
        #     'phase_end': timestamp,
        #     'voice_channel_id': int|None,
        #     'cycle_count': int
        #   }
        # }}
        self.active_sessions = {}
        
        # Start the XP reward task
        self.xp_reward_task.start()
        
        # Start the pomodoro timer check task
        self.pomodoro_timer_task.start()
        
        print("Study cog initialized and database tables created.")

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.xp_reward_task.cancel()
        self.pomodoro_timer_task.cancel()
        
    @tasks.loop(minutes=1)
    async def xp_reward_task(self):
        """Award XP to users in active study sessions every minute"""
        for server_id, session_data in self.active_sessions.items():
            participants = session_data['participants'].copy()  # Copy to avoid modification during iteration
            
            for user_id in participants:
                try:
                    # Ensure user exists in database
                    user_data = self.db_manager.get_user(user_id, server_id)
                    if not user_data:
                        self.db_manager.add_user(user_id, server_id)
                    
                    # Award XP and check for level up
                    leveled_up, new_level, xp_gained = self.db_manager.increment_xp(user_id, server_id)
                    
                    # If user leveled up, send a message
                    if leveled_up:
                        try:
                            guild = self.bot.get_guild(server_id)
                            if guild:
                                user = guild.get_member(user_id)
                                if user:
                                    # Get the channel where the study session was started
                                    channel_id = session_data.get('channel_id')
                                    if channel_id:
                                        channel = guild.get_channel(channel_id)
                                        if channel and channel.permissions_for(guild.me).send_messages:
                                            embed = discord.Embed(
                                                title="📚 Study Level Up!",
                                                description=f"Congratulations {user.mention}! You reached study level **{new_level}** by staying focused!",
                                                color=0x00ff00
                                            )
                                            embed.add_field(name="XP Gained", value=f"+{xp_gained}", inline=True)
                                            await channel.send(embed=embed)
                        except Exception as e:
                            print(f"Error sending level up message: {e}")
                            
                except Exception as e:
                    print(f"Error awarding XP to user {user_id}: {e}")

    @xp_reward_task.before_loop
    async def before_xp_reward_task(self):
        """Wait until bot is ready before starting the task"""
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=30)
    async def pomodoro_timer_task(self):
        """Check pomodoro timers and handle phase transitions"""
        current_time = int(time.time())
        
        for server_id, session_data in self.active_sessions.items():
            pomodoro = session_data.get('pomodoro')
            if not pomodoro or not pomodoro.get('enabled'):
                continue
                
            # Check if current phase has ended
            if current_time >= pomodoro['phase_end']:
                await self.handle_pomodoro_phase_change(server_id, session_data)

    @pomodoro_timer_task.before_loop
    async def before_pomodoro_timer_task(self):
        """Wait until bot is ready before starting the task"""
        await self.bot.wait_until_ready()

    async def handle_pomodoro_phase_change(self, server_id, session_data):
        """Handle transition between work and break phases"""
        try:
            pomodoro = session_data['pomodoro']
            current_phase = pomodoro['current_phase']
            
            # Switch phases
            if current_phase == 'work':
                new_phase = 'break'
                duration = pomodoro['break_duration']
                pomodoro['cycle_count'] += 1
                emoji = "☕"
                message = f"Work session complete! Time for a {duration}-minute break."
            else:
                new_phase = 'work'
                duration = pomodoro['work_duration']
                emoji = "📚"
                message = f"Break time's over! Time for a {duration}-minute work session."
            
            # Update pomodoro data
            current_time = int(time.time())
            pomodoro['current_phase'] = new_phase
            pomodoro['phase_start'] = current_time
            pomodoro['phase_end'] = current_time + (duration * 60)
            
            # Get guild and channel
            guild = self.bot.get_guild(server_id)
            if not guild:
                return
                
            channel = guild.get_channel(session_data['channel_id'])
            if not channel:
                return
            
            # Create embed notification
            embed = discord.Embed(
                title=f"{emoji} Pomodoro Timer",
                description=message,
                color=0xff6b6b if new_phase == 'break' else 0x4ecdc4
            )
            embed.add_field(name="Cycle", value=f"{pomodoro['cycle_count']}", inline=True)
            embed.add_field(name="Next Phase", value=f"<t:{pomodoro['phase_end']}:R>", inline=True)
            
            # Send notification to text channel
            await channel.send(embed=embed)
            
            # Play voice notification if voice channel is set
            voice_channel_id = pomodoro.get('voice_channel_id')
            if voice_channel_id:
                voice_channel = guild.get_channel(voice_channel_id)
                if voice_channel:
                    await self.play_notification_sound(voice_channel, new_phase)
                    
        except Exception as e:
            print(f"Error handling pomodoro phase change: {e}")

    async def play_notification_sound(self, voice_channel, phase):
        """Play notification sound in voice channel"""
        try:
            # Check if bot is already in a voice channel
            if voice_channel.guild.voice_client:
                return
                
            # Join voice channel
            voice_client = await voice_channel.connect()
            
            # Create notification sound file path
            sound_file = f"sounds/pomodoro_{phase}.mp3"
            
            # Check if sound file exists, if not use a default beep
            if not os.path.exists(sound_file):
                # Create a simple beep sound programmatically if no sound file exists
                sound_file = "sounds/notification.mp3"
                if not os.path.exists(sound_file):
                    # If no sound files exist, just disconnect
                    await voice_client.disconnect()
                    return
            
            # Play the sound
            if os.path.exists(sound_file):
                source = discord.FFmpegPCMAudio(sound_file)
                voice_client.play(source)
                
                # Wait for sound to finish playing
                while voice_client.is_playing():
                    await asyncio.sleep(0.1)
            
            # Disconnect after playing
            await voice_client.disconnect()
            
        except Exception as e:
            print(f"Error playing notification sound: {e}")
            # Make sure to disconnect if there's an error
            if voice_channel.guild.voice_client:
                await voice_channel.guild.voice_client.disconnect()
        
    @app_commands.command(name='study', description='Start or join a study session to earn XP')
    async def study(self, interaction: discord.Interaction):
        """Starts a study session with buttons to join/leave."""
        server_id = interaction.guild.id
        
        # Check if there's already an active session
        if server_id in self.active_sessions:
            session_data = self.active_sessions[server_id]
            participant_count = len(session_data['participants'])
            
            embed = discord.Embed(
                title="📚 Active Study Session",
                description="A study session is already running! Join or leave using the buttons below.",
                color=0x0099ff
            )
            embed.add_field(name="Participants", value=str(participant_count), inline=True)
            embed.add_field(name="Session ID", value=str(session_data['session_id']), inline=True)
            
            # Show current participants
            if participant_count > 0:
                participant_mentions = []
                for user_id in list(session_data['participants'])[:10]:  # Show max 10 participants
                    user = interaction.guild.get_member(user_id)
                    if user:
                        participant_mentions.append(user.mention)
                
                if participant_mentions:
                    embed.add_field(
                        name="Current Participants", 
                        value="\n".join(participant_mentions) + ("..." if participant_count > 10 else ""),
                        inline=False
                    )
        else:
            embed = discord.Embed(
                title="📚 Study Session",
                description="Start a new study session! Join to earn XP every minute you study.",
                color=0x0099ff
            )
            embed.add_field(name="XP Reward", value="15-25 XP per minute", inline=True)
        
        view = StudySessionView(self, server_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name='pomodoro', description='Set up a pomodoro timer for the current study session')
    @app_commands.describe(
        work_minutes='Duration of work sessions in minutes (default: 25)',
        break_minutes='Duration of break sessions in minutes (default: 5)',
        voice_channel='Voice channel to play notifications in (optional)'
    )
    async def pomodoro(self, interaction: discord.Interaction, work_minutes: int = 25, break_minutes: int = 5, voice_channel: discord.VoiceChannel = None):
        """Set up pomodoro timer for the current study session"""
        server_id = interaction.guild.id
        
        # Check if there's an active session
        if server_id not in self.active_sessions:
            await interaction.response.send_message(
                "❌ No active study session found! Use `/study` to start a session first.",
                ephemeral=True
            )
            return
        
        # Validate inputs
        if work_minutes < 1 or work_minutes > 120:
            await interaction.response.send_message(
                "❌ Work duration must be between 1 and 120 minutes.",
                ephemeral=True
            )
            return
            
        if break_minutes < 1 or break_minutes > 60:
            await interaction.response.send_message(
                "❌ Break duration must be between 1 and 60 minutes.",
                ephemeral=True
            )
            return
        
        # Set up pomodoro timer
        current_time = int(time.time())
        session_data = self.active_sessions[server_id]
        
        session_data['pomodoro'] = {
            'enabled': True,
            'work_duration': work_minutes,
            'break_duration': break_minutes,
            'current_phase': 'work',
            'phase_start': current_time,
            'phase_end': current_time + (work_minutes * 60),
            'voice_channel_id': voice_channel.id if voice_channel else None,
            'cycle_count': 1
        }
        
        embed = discord.Embed(
            title="⏰ Pomodoro Timer Started!",
            description=f"Timer configured for the current study session.",
            color=0x4ecdc4
        )
        embed.add_field(name="Work Duration", value=f"{work_minutes} minutes", inline=True)
        embed.add_field(name="Break Duration", value=f"{break_minutes} minutes", inline=True)
        embed.add_field(name="Current Phase", value="📚 Work", inline=True)
        embed.add_field(name="Phase Ends", value=f"<t:{session_data['pomodoro']['phase_end']}:R>", inline=True)
        embed.add_field(name="Cycle", value="1", inline=True)
        
        if voice_channel:
            embed.add_field(name="Voice Notifications", value=f"#{voice_channel.name}", inline=True)
        else:
            embed.add_field(name="Voice Notifications", value="Disabled", inline=True)
        
        view = PomodoroControlView(self, server_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name='pomoinfo', description='View information about the current pomodoro timer')
    async def pomodoro_info(self, interaction: discord.Interaction):
        """Display current pomodoro timer information"""
        server_id = interaction.guild.id
        
        if server_id not in self.active_sessions:
            await interaction.response.send_message(
                "❌ No active study session found!",
                ephemeral=True
            )
            return
        
        session_data = self.active_sessions[server_id]
        pomodoro = session_data.get('pomodoro')
        
        if not pomodoro or not pomodoro.get('enabled'):
            await interaction.response.send_message(
                "❌ No pomodoro timer is active for this session!",
                ephemeral=True
            )
            return
        
        current_phase = pomodoro['current_phase']
        phase_emoji = "📚" if current_phase == 'work' else "☕"
        phase_name = current_phase.capitalize()
        
        embed = discord.Embed(
            title=f"{phase_emoji} Pomodoro Timer Status",
            description=f"Currently in {phase_name} phase",
            color=0x4ecdc4 if current_phase == 'work' else 0xff6b6b
        )
        embed.add_field(name="Work Duration", value=f"{pomodoro['work_duration']} minutes", inline=True)
        embed.add_field(name="Break Duration", value=f"{pomodoro['break_duration']} minutes", inline=True)
        embed.add_field(name="Current Cycle", value=f"{pomodoro['cycle_count']}", inline=True)
        embed.add_field(name="Phase Ends", value=f"<t:{pomodoro['phase_end']}:R>", inline=True)
        
        voice_channel_id = pomodoro.get('voice_channel_id')
        if voice_channel_id:
            voice_channel = interaction.guild.get_channel(voice_channel_id)
            if voice_channel:
                embed.add_field(name="Voice Notifications", value=f"#{voice_channel.name}", inline=True)
        
        participants = len(session_data['participants'])
        embed.add_field(name="Participants", value=f"{participants} studying", inline=True)
        
        await interaction.response.send_message(embed=embed)

    async def stop_pomodoro(self, interaction, server_id):
        """Stop the pomodoro timer for a session"""
        if server_id in self.active_sessions:
            session_data = self.active_sessions[server_id]
            if 'pomodoro' in session_data:
                session_data['pomodoro']['enabled'] = False
                await interaction.response.send_message(
                    "⏰ Pomodoro timer stopped!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ No pomodoro timer is active!",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "❌ No active study session found!",
                ephemeral=True
            )

    async def join_session(self, interaction, server_id):
        """Handle user joining a study session"""
        user_id = interaction.user.id
        
        # Create session if it doesn't exist
        if server_id not in self.active_sessions:
            session_id = self.db_manager.start_study_session(server_id)
            self.active_sessions[server_id] = {
                'session_id': session_id,
                'participants': set(),
                'start_time': int(time.time()),
                'channel_id': interaction.channel.id
            }
        
        # Add user to session
        if user_id not in self.active_sessions[server_id]['participants']:
            self.active_sessions[server_id]['participants'].add(user_id)
            
            # Ensure user exists in database
            user_data = self.db_manager.get_user(user_id, server_id)
            if not user_data:
                self.db_manager.add_user(user_id, server_id)
            
            # Update user's session info
            self.db_manager.update_user_session(user_id, server_id, self.active_sessions[server_id]['session_id'])
            
            participant_count = len(self.active_sessions[server_id]['participants'])
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} joined the study session! ({participant_count} participants)\n"
                f"You'll earn 15-25 XP every minute while studying. Good luck! 📖",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "You're already in this study session! Keep up the good work! 💪",
                ephemeral=True
            )

    async def leave_session(self, interaction, server_id):
        """Handle user leaving a study session"""
        user_id = interaction.user.id
        
        if server_id in self.active_sessions and user_id in self.active_sessions[server_id]['participants']:
            # Calculate study time for this user
            session_start = self.active_sessions[server_id]['start_time']
            study_duration = max(0, (int(time.time()) - session_start) // 60)  # Duration in minutes
            
            # Update user's total study time
            if study_duration > 0:
                self.db_manager.update_total_study_time(user_id, server_id, study_duration)
            
            # Remove user from session
            self.active_sessions[server_id]['participants'].remove(user_id)
            participant_count = len(self.active_sessions[server_id]['participants'])
            
            # End session if no participants left
            if participant_count == 0:
                self.db_manager.end_study_session(self.active_sessions[server_id]['session_id'])
                del self.active_sessions[server_id]
                await interaction.response.send_message(
                    f"👋 {interaction.user.mention} left the study session.\n"
                    f"Session ended as no participants remain. You studied for {study_duration} minutes total!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"👋 {interaction.user.mention} left the study session. ({participant_count} participants remaining)\n"
                    f"You studied for {study_duration} minutes this session. Great work!",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "You're not currently in a study session!",
                ephemeral=True
            )

    @app_commands.command(name='studystats', description='View study statistics for yourself or another user')
    @app_commands.describe(user='The user to view stats for (optional, defaults to yourself)')
    async def study_stats(self, interaction: discord.Interaction, user: discord.Member = None):
        """Display study statistics for a user"""
        target_user = user or interaction.user
        user_data = self.db_manager.get_user(target_user.id, interaction.guild.id)
        
        if not user_data:
            await interaction.response.send_message(f"{target_user.display_name} hasn't started studying yet!")
            return
        
        # user_data format: (userid, serverid, last_study_session_time, last_study_session_id, total_study_time, user_xp, user_level)
        total_time = user_data[4]
        xp = user_data[5]
        level = user_data[6]
        
        # Calculate XP needed for next level
        next_level_xp = 5 * (level * level) + 50 * level + 100
        xp_needed = next_level_xp - xp
        
        embed = discord.Embed(
            title=f"📊 Study Stats for {target_user.display_name}",
            color=0x0099ff
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Study Level", value=str(level), inline=True)
        embed.add_field(name="Current XP", value=f"{xp}/{next_level_xp}", inline=True)
        embed.add_field(name="XP to Next Level", value=str(xp_needed), inline=True)
        embed.add_field(name="Total Study Time", value=f"{total_time} minutes", inline=True)
        embed.add_field(name="Hours Studied", value=f"{total_time/60:.1f} hours", inline=True)
        
        # Check if user is currently in a session
        server_id = interaction.guild.id
        if server_id in self.active_sessions and target_user.id in self.active_sessions[server_id]['participants']:
            embed.add_field(name="Status", value="🟢 Currently Studying", inline=True)
        else:
            embed.add_field(name="Status", value="🔴 Not in Session", inline=True)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='studyleaderboard', description='View the study leaderboard for this server')
    async def study_leaderboard(self, interaction: discord.Interaction):
        """Display the study leaderboard for the server"""
        # Add method to get leaderboard data
        leaderboard_data = self.db_manager.get_leaderboard(interaction.guild.id)
        
        if not leaderboard_data:
            await interaction.response.send_message("No study data available yet! Start studying to appear on the leaderboard!")
            return
        
        embed = discord.Embed(
            title="📚 Study Leaderboard",
            description="Top studiers in this server",
            color=0xffd700
        )
        
        for i, (user_id, total_time, xp, level) in enumerate(leaderboard_data[:10], 1):
            user = interaction.guild.get_member(user_id)
            if user:
                # Add medal emojis for top 3
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈"
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = f"{i}."
                
                embed.add_field(
                    name=f"{medal} {user.display_name}",
                    value=f"Level {level} • {total_time} minutes • {xp} XP",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='help', description='View all available study commands and their descriptions')
    async def help_command(self, interaction: discord.Interaction):
        """Display help information for all study commands"""
        embed = discord.Embed(
            title="📚 Study Bot Help",
            description="Here are all the available study commands:",
            color=0x0099ff
        )
        
        # Add bot information
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name="🎯 About",
            value="This bot gamifies studying by rewarding users with XP for participating in study sessions!",
            inline=False
        )
        
        # Study command
        embed.add_field(
            name="📖 `/study`",
            value="Start or join a study session. Earn 15-25 XP every minute while studying!\n"
                  "• Creates a new session if none exists\n"
                  "• Join an existing session with interactive buttons\n"
                  "• Leave anytime to save your progress",
            inline=False
        )
        
        # Pomodoro command
        embed.add_field(
            name="⏰ `/pomodoro [work_minutes] [break_minutes] [voice_channel]`",
            value="Set up a pomodoro timer for the current study session.\n"
                  "• Default: 25 minutes work, 5 minutes break\n"
                  "• Optional voice channel for audio notifications\n"
                  "• Automatically switches between work and break phases",
            inline=False
        )
        
        # Pomodoro info command
        embed.add_field(
            name="📊 `/pomoinfo`",
            value="View information about the current pomodoro timer.\n"
                  "• Shows current phase (work/break)\n"
                  "• Displays time remaining and cycle count\n"
                  "• Shows timer configuration",
            inline=False
        )
        
        # Study stats command
        embed.add_field(
            name="📊 `/studystats [user]`",
            value="View detailed study statistics for yourself or another user.\n"
                  "• Shows current level and XP\n"
                  "• Displays total study time in minutes and hours\n"
                  "• Shows if currently in an active session\n"
                  "• Leave `user` blank to see your own stats",
            inline=False
        )
        
        # Leaderboard command
        embed.add_field(
            name="🏆 `/studyleaderboard`",
            value="View the top 10 studiers in the server.\n"
                  "• Ranked by level, then XP, then total study time\n"
                  "• Shows medals for top 3 positions\n"
                  "• Updates in real-time as users study",
            inline=False
        )
        
        # Help command
        embed.add_field(
            name="❓ `/help`",
            value="Display this help message with all command descriptions.",
            inline=False
        )
        
        # XP System info
        embed.add_field(
            name="⭐ XP & Leveling System",
            value="• Earn **15-25 XP** every minute in a study session\n"
                  "• Level up formula: `5 × level² + 50 × level + 100` XP per level\n"
                  "• Get notified when you level up!\n"
                  "• Track your progress with `/studystats`",
            inline=False
        )
        
        # Usage tips
        embed.add_field(
            name="💡 Tips",
            value="• Study sessions continue until all participants leave\n"
                  "• Your study time is automatically tracked\n"
                  "• Level up notifications appear in the channel where you started studying\n"
                  "• Use buttons to easily join/leave sessions",
            inline=False
        )
        
        embed.set_footer(text="Happy studying! 📚✨")
        
        await interaction.response.send_message(embed=embed)


class StudySessionView(View):
    def __init__(self, study_cog, server_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.study_cog = study_cog
        self.server_id = server_id
    
    @discord.ui.button(label="Join Study Session", style=discord.ButtonStyle.green, emoji="📚")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        await self.study_cog.join_session(interaction, self.server_id)
    
    @discord.ui.button(label="Leave Session", style=discord.ButtonStyle.red, emoji="👋")
    async def leave_button(self, interaction: discord.Interaction, button: Button):
        await self.study_cog.leave_session(interaction, self.server_id)


class PomodoroControlView(View):
    def __init__(self, study_cog, server_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.study_cog = study_cog
        self.server_id = server_id
    
    @discord.ui.button(label="Stop Timer", style=discord.ButtonStyle.red, emoji="⏰")
    async def stop_timer_button(self, interaction: discord.Interaction, button: Button):
        await self.study_cog.stop_pomodoro(interaction, self.server_id)


async def setup(bot):
    await bot.add_cog(Study(bot))
    print("Study cog loaded successfully.")