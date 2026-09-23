	public static string GetHTMLFullScreenMessageSource(ConversationMessageDto msg)
	{
		int num = default(int);
		string text = default(string);
		short num2;
		switch (0)
		{
		default:
			while (true)
			{
				switch (num)
				{
				case 2:
					goto IL_0049;
				case 4:
					num2 = 1;
					if (num2 != 0)
					{
					}
					num2 = 0;
					num = num2;
					continue;
				case 0:
					goto IL_00cf;
				case 5:
					num2 = 3;
					num = num2;
					continue;
				case 3:
					text = msg.Attachments.Aggregate(text, delegate(string A_0, AttachmentDto A_1)
					{
						short num4 = 30491;
						short num5 = num4;
						num4 = 30491;
						switch (num5 == num4)
						{
						default:
							num4 = 0;
							if (num4 != 0)
							{
							}
							num4 = 1;
							if (num4 != 0)
							{
							}
							return A_0 + GetHTMLChatAttachmentSource(A_1);
						}
					});
					num2 = 1;
					num = num2;
					continue;
				case 1:
					goto IL_0171;
				}
				break;
				IL_0171:
				num2 = 1887;
				short num3 = num2;
				num2 = 1887;
				switch (num3 == num2)
				{
				case false:
				case true:
					break;
				default:
					goto IL_01b1;
				}
				goto IL_002e;
				IL_01b1:
				num2 = 0;
				if (num2 == 0)
				{
				}
				goto IL_01d4;
				IL_00cf:
				if (msg.Attachments.Any())
				{
					num2 = 5;
					num = num2;
					continue;
				}
				goto IL_01d4;
				IL_01d4:
				return $"\n                        <article>\n                            <header>\n                                {msg.SenderFullName}\n                                <span>{msg.Date:dddd dd MMM yyyy HH:mm}</span>\n                            </header>\n                            <section>\n                                {text}\n                                {WebUtility.HtmlDecode(msg.Body)}\n                            </section>\n                        </article>\n                ";
				IL_0049:
				if (msg.Attachments != null)
				{
					num2 = 4;
					num = num2;
					continue;
				}
				goto IL_01d4;
			}
			goto case 0;
		case 0:
			{
				text = string.Empty;
				goto IL_002e;
			}
			IL_002e:
			num2 = 2;
			num = num2;
			goto default;
		}
	}
