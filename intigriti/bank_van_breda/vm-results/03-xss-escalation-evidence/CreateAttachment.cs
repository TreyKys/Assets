using System.Runtime.CompilerServices;
using BVB.EOS.OnlineBanking.UI.Mobile.Services.ApiServices.App.Contracts.Base;
using BVB.Toolkit.Client.Net;

namespace BVB.EOS.OnlineBanking.UI.Mobile.Services.ApiServices.App.Contracts;

public class CreateAttachment : BaseRequest, IReturn<CreateAttachmentResponse>, IReturn
{
	[CompilerGenerated]
	private readonly string a;

	[CompilerGenerated]
	private readonly FileInfoDto b;

	public string AttachmentUsageTypeCOID
	{
		[CompilerGenerated]
		get
		{
			short num = -24020;
			short num2 = num;
			num = -24020;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return a;
			}
		}
		[CompilerGenerated]
		init
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = -301;
			short num2 = num;
			num = -301;
			switch (num2 == num)
			{
			}
			num = 0;
			if (num != 0)
			{
			}
			a = value;
		}
	}

	public FileInfoDto Attachment
	{
		[CompilerGenerated]
		get
		{
			short num = 12851;
			short num2 = num;
			num = 12851;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return b;
			}
		}
		[CompilerGenerated]
		init
		{
			short num = 6153;
			short num2 = num;
			num = 6153;
			switch (num2 == num)
			{
			}
			num = 0;
			if (num != 0)
			{
			}
			num = 1;
			if (num != 0)
			{
			}
			b = value;
		}
	}
}
