import os
import random
import discord
from discord import app_commands
from discord.ext import commands
from deep_translator import GoogleTranslator
from openai import OpenAI

TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("OPENAI_API_KEY")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
client = OpenAI(api_key=API_KEY) if API_KEY else None

scores = {}
questions = [
    ("ما عاصمة الجزائر؟", ["الجزائر"], "الجزائر"),
    ("كم يساوي 5 + 5؟", ["10", "عشرة"], "10"),
    ("ما الكوكب المعروف بالكوكب الأحمر؟", ["المريخ"], "المريخ"),
    ("What is 2 + 2?", ["4", "four"], "4"),
]

async def ai_response(prompt):
    if not client:
        return "ميزة الذكاء الاصطناعي غير مفعلة بعد. يجب إعداد OPENAI_API_KEY."
    try:
        result = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت Ameen AI، مساعد ودود. "
                        "أجب بلغة المستخدم، واشرح الرسائل ونبرتها المحتملة "
                        "واقترح ردودًا مناسبة دون الجزم بنوايا الآخرين."
                    )
                },
                {"role": "user", "content": prompt[:4000]}
            ],
            max_tokens=500
        )
        return result.choices[0].message.content or "لم أجد إجابة."
    except Exception:
        return "حدث خطأ أثناء الاتصال بالذكاء الاصطناعي."

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Ameen AI is online: {bot.user}")

@bot.tree.command(name="help", description="عرض أوامر Ameen AI")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**🤖 Ameen AI**\n"
        "`/explain` شرح رسالة واقتراح رد\n"
        "`/ask` التحدث مع الذكاء الاصطناعي\n"
        "`/translate` ترجمة النصوص\n"
        "`/trivia` بدء مسابقة\n"
        "`/top` ترتيب النقاط",
        ephemeral=True
    )

@bot.tree.command(name="ask", description="اسأل Ameen AI")
@app_commands.describe(question="اكتب سؤالك")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    answer = await ai_response(question)
    await interaction.followup.send(answer[:1900])

@bot.tree.command(name="explain", description="افهم رسالة واقترح ردًا")
@app_commands.describe(text="الرسالة التي تريد فهمها")
async def explain(interaction: discord.Interaction, text: str):
    await interaction.response.defer(thinking=True, ephemeral=True)
    answer = await ai_response(
        "اشرح معنى الرسالة التالية، وما النبرة المحتملة فيها، "
        "ثم اقترح ردين مناسبين. لا تفترض نوايا مؤكدة.\n\n" + text
    )
    await interaction.followup.send(answer[:1900], ephemeral=True)

@bot.tree.command(name="translate", description="ترجمة نص")
@app_commands.describe(text="النص", language="رمز اللغة مثل ar أو en أو fr")
async def translate(
    interaction: discord.Interaction,
    text: str,
    language: str = "ar"
):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        translated = GoogleTranslator(
            source="auto", target=language.lower()
        ).translate(text[:4000])
        await interaction.followup.send(translated[:1900], ephemeral=True)
    except Exception:
        await interaction.followup.send(
            "تعذرت الترجمة. تحقق من رمز اللغة وحاول مجددًا.",
            ephemeral=True
        )

@bot.tree.command(name="trivia", description="سؤال مسابقة واربح نقطة")
async def trivia(interaction: discord.Interaction):
    question, answers, correct = random.choice(questions)
    await interaction.response.send_message(
        f"🎯 **{question}**\nأول إجابة صحيحة خلال 30 ثانية تفوز بنقطة!"
    )

    def check(message):
        return (
            message.channel == interaction.channel
            and not message.author.bot
            and message.content.strip().lower()
            in [answer.lower() for answer in answers]
        )

    try:
        message = await bot.wait_for(
            "message", timeout=30, check=check
        )
        scores[message.author.id] = scores.get(message.author.id, 0) + 1
        await interaction.followup.send(
            f"🏆 أحسنت {message.author.mention}! حصلت على نقطة."
        )
    except TimeoutError:
        await interaction.followup.send(
            f"انتهى الوقت! الإجابة الصحيحة: **{correct}**"
        )

@bot.tree.command(name="top", description="عرض ترتيب المسابقة")
async def top(interaction: discord.Interaction):
    if not scores:
        await interaction.response.send_message(
            "لا توجد نقاط بعد. استخدم /trivia للبدء!"
        )
        return

    ranking = sorted(
        scores.items(), key=lambda item: item[1], reverse=True
    )[:10]

    lines = []
    for position, (user_id, points) in enumerate(ranking, 1):
        user = bot.get_user(user_id)
        name = user.display_name if user else str(user_id)
        lines.append(f"**{position}.** {name} — {points} نقطة")

    await interaction.response.send_message(
        "🏆 **أفضل اللاعبين**\n" + "\n".join(lines)
    )

if not TOKEN:
    raise RuntimeError("ضع DISCORD_TOKEN في متغيرات البيئة.")

bot.run(TOKEN)
